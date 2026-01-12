"""
Crawler Service - Web scraping and crawling logic

Handles asynchronous fetching, parsing, and recursive crawling with domain boundary checking.
Includes support for Cloudflare and other protection mechanisms.
"""

import asyncio
import logging
import re
import requests
from datetime import datetime
from typing import Set, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup
import cloudscraper
import chardet

from ..core.config import settings
from ..schemas.crawler import PageContent, ImageData, CrawlResponse
from .vector_db_service import vector_db_service

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for web crawling and scraping operations"""

    # Realistic browser headers to avoid 403 Forbidden
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    def __init__(self):
        self.settings = settings
        self.session: Optional[httpx.AsyncClient] = None
        self.scraper: Optional[cloudscraper.CloudScraper] = None  # For Cloudflare bypass
        self.executor = ThreadPoolExecutor(max_workers=self.settings.MAX_CONCURRENT_REQUESTS)
        self.visited_urls: Set[str] = set()
        self.crawl_queue: deque = deque()
        self.base_domain: Optional[str] = None
        self.pages_data: List[PageContent] = []
        self.errors: List[str] = []
        self.current_url: Optional[str] = None  # Track current URL for Referer header

    async def __aenter__(self):
        """Context manager entry - initialize HTTP clients"""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.REQUEST_TIMEOUT, connect=10.0),
            headers=self.HEADERS,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=self.settings.MAX_CONCURRENT_REQUESTS),
            verify=True,
        )
        # Initialize cloudscraper for protected sites
        self.scraper = cloudscraper.create_scraper()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close HTTP clients"""
        if self.session:
            await self.session.aclose()
        if self.executor:
            self.executor.shutdown(wait=False)

    def _extract_domain(self, url: str) -> str:
        """Extract base domain from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _get_root_domain(self, url: str) -> str:
        """Extract root domain without www"""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Remove www. prefix for comparison
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and within base domain"""
        try:
            parsed = urlparse(url)
            # Skip non-http(s) protocols
            if parsed.scheme not in ("http", "https"):
                return False

            # Check if URL is within base domain (flexible comparison)
            if self.base_domain:
                url_root = self._get_root_domain(url)
                base_root = self._get_root_domain(self.base_domain)
                return url_root == base_root

            return True
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalize and resolve relative URLs to absolute URLs"""
        try:
            if not url.strip():
                return None

            # Skip fragments and anchors
            if url.startswith("#"):
                return None

            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, url)

            # Remove fragments
            absolute_url = absolute_url.split("#")[0]

            return absolute_url if absolute_url else None
        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {str(e)}")
            return None

    async def _fetch_page(self, url: str, referer: Optional[str] = None) -> Optional[Tuple[str, int]]:
        """
        Fetch a single page asynchronously with retry mechanism
        Uses cloudscraper for protected sites, falls back to httpx

        Returns:
            Tuple of (content, status_code) or None on error
        """
        if not self.session:
            logger.error("Session not initialized")
            return None

        max_retries = self.settings.MAX_RETRIES
        retry_delay = self.settings.RETRY_DELAY

        for attempt in range(max_retries):
            try:
                # Add dynamic Referer header
                headers = dict(self.HEADERS)
                if referer:
                    headers["Referer"] = referer
                else:
                    headers["Referer"] = self.base_domain or url

                # Try with cloudscraper first (better for protected sites)
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        self.executor,
                        lambda: self.scraper.get(url, headers=headers, timeout=self.settings.REQUEST_TIMEOUT)
                    )
                    
                    if response.status_code == 200:
                        # Ensure proper encoding for cloudscraper response
                        try:
                            # Use chardet to detect encoding from raw bytes
                            detected = chardet.detect(response.content)
                            encoding = detected.get('encoding', 'utf-8')
                            if detected.get('confidence', 0) > 0.7:
                                response.encoding = encoding
                            elif response.apparent_encoding:
                                response.encoding = response.apparent_encoding
                            else:
                                response.encoding = 'utf-8'
                        except Exception:
                            response.encoding = response.apparent_encoding or 'utf-8'
                        return response.text, response.status_code
                    elif response.status_code == 403:
                        logger.warning(f"HTTP 403 Forbidden for {url} (cloudscraper)")
                        # Try with httpx if cloudscraper gets 403
                        raise Exception("Cloudscraper failed, trying httpx")
                    elif response.status_code == 404:
                        error_msg = f"HTTP 404 Not Found for {url}"
                        logger.warning(error_msg)
                        self.errors.append(error_msg)
                        return None
                    else:
                        logger.debug(f"Cloudscraper returned {response.status_code}, trying httpx")
                        raise Exception(f"Status {response.status_code}")
                except Exception as cloud_error:
                    # Fallback to httpx
                    logger.debug(f"Cloudscraper failed: {cloud_error}, using httpx")
                    response = await self.session.get(
                        url,
                        headers=headers,
                        follow_redirects=True,
                    )

                    if response.status_code == 200:
                        # Handle encoding properly for httpx
                        try:
                            # Get raw bytes
                            content = response.content
                            
                            # Use chardet for robust encoding detection
                            detected = chardet.detect(content)
                            encoding = detected.get('encoding')
                            confidence = detected.get('confidence', 0)
                            
                            # Use detected encoding if confidence is high
                            if encoding and confidence > 0.7:
                                try:
                                    text = content.decode(encoding, errors='ignore')
                                    return text, response.status_code
                                except (UnicodeDecodeError, LookupError):
                                    pass
                            
                            # Try charset from response header
                            if response.charset_encoding:
                                try:
                                    text = content.decode(response.charset_encoding, errors='ignore')
                                    return text, response.status_code
                                except (UnicodeDecodeError, LookupError):
                                    pass
                            
                            # Final fallback to utf-8
                            text = content.decode('utf-8', errors='replace')
                            return text, response.status_code
                        except Exception as decode_error:
                            logger.warning(f"Encoding issue for {url}: {decode_error}, using response.text")
                            return response.text, response.status_code

                    elif response.status_code == 403:
                        error_msg = f"HTTP 403 Forbidden for {url}"
                        logger.warning(error_msg)
                        # Don't retry on 403, it's likely intentional blocking
                        self.errors.append(error_msg)
                        return None

                    elif response.status_code == 404:
                        error_msg = f"HTTP 404 Not Found for {url}"
                        logger.warning(error_msg)
                        self.errors.append(error_msg)
                        return None

                    elif response.status_code in (429, 503):
                        # Retry on rate limit and service unavailable
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"HTTP {response.status_code} for {url}, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_msg = f"HTTP {response.status_code} for {url} (after {max_retries} retries)"
                            logger.error(error_msg)
                            self.errors.append(error_msg)
                            return None

                    else:
                        error_msg = f"HTTP {response.status_code} for {url}"
                        logger.warning(error_msg)
                        self.errors.append(error_msg)
                        return None

            except httpx.TimeoutException as e:
                error_msg = f"Timeout while fetching {url}"
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"{error_msg}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{error_msg} (after {max_retries} retries)")
                    self.errors.append(error_msg)
                    return None

            except httpx.ConnectError as e:
                error_msg = f"Connection error for {url}: {str(e)}"
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"{error_msg}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{error_msg} (after {max_retries} retries)")
                    self.errors.append(error_msg)
                    return None

            except httpx.RequestError as e:
                error_msg = f"Request error for {url}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return None

            except Exception as e:
                error_msg = f"Unexpected error fetching {url}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return None

        return None

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid links from a page - improved extraction"""
        links = []
        seen_in_batch = set()
        
        try:
            # Find all anchor tags with href
            all_anchors = soup.find_all("a", href=True)
            logger.debug(f"Found {len(all_anchors)} anchor tags on {current_url}")
            
            for link in all_anchors:
                href = link.get("href", "").strip()
                
                # Skip empty, fragments, javascript, etc.
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                
                normalized_url = self._normalize_url(href, current_url)

                if normalized_url and self._is_valid_url(normalized_url):
                    if normalized_url not in self.visited_urls and normalized_url not in seen_in_batch:
                        links.append(normalized_url)
                        seen_in_batch.add(normalized_url)
            
            logger.info(f"Extracted {len(links)} unique valid links from {current_url}")
            
        except Exception as e:
            logger.error(f"Error extracting links from {current_url}: {str(e)}")

        return links

    def _extract_images(self, soup: BeautifulSoup, page_url: str) -> List[ImageData]:
        """Extract all images from a page and normalize their URLs"""
        images = []
        try:
            for img in soup.find_all("img"):
                src = img.get("src", "").strip()
                alt = img.get("alt", "").strip()

                if src:
                    # Normalize image URL to absolute
                    absolute_src = self._normalize_url(src, page_url)
                    if absolute_src:
                        images.append(ImageData(url=absolute_src, alt_text=alt if alt else None))
                    else:
                        # If normalization fails, use original src
                        images.append(ImageData(url=src, alt_text=alt if alt else None))
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")

        return images

    def _extract_text_content(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """
        Extract text content from page with robust HTML parsing
        Filters out encoded/minified content and JavaScript

        Returns:
            Tuple of (full_content, snippet)
        """
        try:
            # Remove all script, style, and other non-content elements
            for element in soup(["script", "style", "meta", "link", "noscript", "iframe", "nav", "footer"]):
                element.decompose()

            # Try to get content from main content areas first
            main_content = None
            for selector in ["main", "article", ".content", ".main-content", "#content", ".post"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.find("body")
            if not main_content:
                main_content = soup

            # Extract text from paragraphs, headings, and lists primarily
            text_parts = []
            for element in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "span", "div"]):
                text = element.get_text(strip=True)
                if text and len(text) > 3:  # Skip very short text
                    text_parts.append(text)

            # If no structured content found, fallback to all text
            if not text_parts:
                text = main_content.get_text(separator=" ", strip=True)
            else:
                text = " ".join(text_parts)

            # Clean up text - remove extra whitespace
            text = " ".join(text.split())

            # Filter out encoded/minified patterns
            # Remove long hex strings (often from minified code)
            text = re.sub(r'[a-f0-9\s]{100,}', '', text, flags=re.IGNORECASE)
            # Remove very long words without spaces (minified code)
            text = re.sub(r'\S{150,}', '', text)
            # Remove Unicode symbols that might be garbage
            text = re.sub(r'[\u2190-\u21FF\u25A0-\u25FF\u2600-\u27BF]', '', text)
            
            # Check if text looks like gibberish (mostly non-ASCII chars)
            ascii_chars = sum(1 for c in text if ord(c) < 128)
            total_chars = len(text.replace(" ", ""))
            if total_chars > 0 and ascii_chars / total_chars < 0.3:
                # Less than 30% ASCII, likely encoded content
                logger.debug("Detected encoded/minified content, skipping")
                return "", ""

            # Normalize whitespace again
            text = " ".join(text.split())

            # Skip if content is still too short after filtering
            if len(text) < 20:
                return "", ""

            # Limit content length
            if len(text) > self.settings.MAX_CONTENT_LENGTH:
                text = text[: self.settings.MAX_CONTENT_LENGTH]

            # Create snippet
            snippet = text[: self.settings.CONTENT_SNIPPET_LENGTH]
            if len(text) > self.settings.CONTENT_SNIPPET_LENGTH:
                snippet += "..."

            return text, snippet
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            return "", ""

    def _parse_page(self, url: str, content: str) -> Tuple[Optional[PageContent], List[str]]:
        """
        Parse page content and extract data using robust HTML parser

        Returns:
            Tuple of (PageContent, list_of_discovered_links)
        """
        try:
            # Use lxml parser for better HTML handling, fallback to html.parser
            try:
                soup = BeautifulSoup(content, "lxml")
            except Exception:
                logger.debug("lxml parser not available, using html.parser")
                soup = BeautifulSoup(content, "html.parser")

            # Extract page title
            title = None
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                # Try meta og:title as fallback
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    title = og_title.get("content", "").strip()

            # Extract content and snippet
            full_content, snippet = self._extract_text_content(soup)

            # Skip pages with very little content
            if not full_content or len(full_content.strip()) < 20:
                logger.debug(f"Skipping {url} - insufficient content")
                return None, []

            # Extract images with normalized URLs
            images = self._extract_images(soup, url)

            # Extract links for crawling
            links = self._extract_links(soup, url)

            # Create PageContent object
            page = PageContent(
                url=url,
                title=title,
                text_content=full_content,
                content_snippet=snippet,
                images=images,
                images_count=len(images),
                crawl_timestamp=datetime.utcnow().isoformat() + "Z",
            )

            return page, links
        except Exception as e:
            logger.error(f"Error parsing page {url}: {str(e)}")
            return None, []

    async def crawl(
        self, seed_url: str, max_pages: int = 50, follow_external_links: bool = False
    ) -> CrawlResponse:
        """
        Main crawling method - performs recursive crawling with async concurrency

        Args:
            seed_url: Starting URL to crawl
            max_pages: Maximum number of pages to crawl
            follow_external_links: Whether to follow links outside base domain

        Returns:
            CrawlResponse with all crawled pages and metadata
        """
        start_time = datetime.utcnow()

        # Initialize crawler state
        self.visited_urls.clear()
        self.pages_data.clear()
        self.errors.clear()
        self.crawl_queue.clear()

        # Set base domain
        self.base_domain = self._extract_domain(seed_url)

        # Add seed URL to queue
        self.crawl_queue.append(seed_url)
        self.visited_urls.add(seed_url)

        logger.info(f"Starting crawl from {seed_url}")

        # Crawl pages with concurrency control
        async with self:
            while self.crawl_queue and len(self.pages_data) < max_pages:
                # Get batch of URLs to process
                batch_size = min(
                    self.settings.MAX_CONCURRENT_REQUESTS,
                    len(self.crawl_queue),
                    max_pages - len(self.pages_data),
                )
                batch = [self.crawl_queue.popleft() for _ in range(batch_size)]

                # Fetch pages concurrently
                tasks = [self._fetch_page(url) for url in batch]
                results = await asyncio.gather(*tasks)

                # Process results
                for url, fetch_result in zip(batch, results):
                    if len(self.pages_data) >= max_pages:
                        break

                    if fetch_result is None:
                        continue

                    content, status_code = fetch_result

                    # Parse page and extract data
                    page, discovered_links = self._parse_page(url, content)

                    if page:
                        self.pages_data.append(page)
                        logger.info(f"Crawled: {url} ({len(self.pages_data)}/{max_pages})")

                        # Add discovered links to queue
                        added_links = 0
                        for link in discovered_links:
                            if link not in self.visited_urls and len(self.pages_data) < max_pages:
                                self.visited_urls.add(link)
                                self.crawl_queue.append(link)
                                added_links += 1
                        
                        logger.info(f"Added {added_links} new links to queue (queue size: {len(self.crawl_queue)})")

                # Add small delay between batches to avoid overwhelming server
                if self.crawl_queue and len(self.pages_data) < max_pages:
                    await asyncio.sleep(0.5)

        # Calculate crawl duration
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Crawl completed: {len(self.pages_data)} pages in {duration:.2f}s")
        
        # Store in vector database if enabled
        vector_stats = None
        if vector_db_service.enabled and self.pages_data:
            logger.info("Storing crawled content in vector database...")
            vector_stats = await vector_db_service.store_pages_batch(self.pages_data, seed_url)
            logger.info(f"Vector storage: {vector_stats}")

        # Return response
        response_data = {
            "success": True,
            "base_url": seed_url,
            "total_pages_crawled": len(self.pages_data),
            "total_pages_requested": len(self.visited_urls),
            "pages": self.pages_data,
            "errors": self.errors,
            "crawl_duration_seconds": duration,
        }
        
        # Add vector stats if available
        if vector_stats:
            response_data["vector_storage"] = vector_stats
        
        return CrawlResponse(**response_data)


# Singleton instance
crawler_service = CrawlerService()
