"""
Database Service - Store crawled content to PostgreSQL
"""

import logging
import hashlib
from typing import List, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from ..models.content_manager import ContentManager
from ..schemas.crawler import PageContent
from .crawler import logger as crawler_logger

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for storing crawled data to PostgreSQL database"""
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""
    
    @staticmethod
    def _calculate_content_hash(content: str) -> str:
        """Calculate SHA-256 hash of content for deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _calculate_word_count(text: str) -> int:
        """Calculate word count from text"""
        return len(text.split()) if text else 0
    
    @staticmethod
    def store_page(db: Session, page: PageContent, base_url: str) -> bool:
        """Store a single crawled page in the database"""
        try:
            domain = DatabaseService._extract_domain(page.url)
            content_hash = DatabaseService._calculate_content_hash(page.text_content)
            word_count = DatabaseService._calculate_word_count(page.text_content)
            
            # Convert images to JSONB format
            images_json = [
                {"url": img.url, "alt_text": img.alt_text}
                for img in (page.images or [])
            ]
            
            content_manager = ContentManager(
                url=page.url,
                base_url=base_url,
                domain=domain,
                title=page.title,
                text_content=page.text_content,
                content_snippet=page.content_snippet,
                images=images_json,
                images_count=len(page.images) if page.images else 0,
                content_hash=content_hash,
                word_count=word_count,
                crawl_status='completed',
                http_status_code=200,
                is_processed=True,
            )
            db.add(content_manager)
            db.commit()
            db.refresh(content_manager)
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing page {page.url}: {e}")
            return False
    
    @staticmethod
    def store_pages_batch(db: Session, pages: List[PageContent], base_url: str) -> dict:
        """Store multiple crawled pages in a batch"""
        stored = 0
        failed = 0
        
        try:
            for page in pages:
                try:
                    domain = DatabaseService._extract_domain(page.url)
                    content_hash = DatabaseService._calculate_content_hash(page.text_content)
                    word_count = DatabaseService._calculate_word_count(page.text_content)
                    
                    # Convert images to JSONB format
                    images_json = [
                        {"url": img.url, "alt_text": img.alt_text}
                        for img in (page.images or [])
                    ]
                    
                    content_manager = ContentManager(
                        url=page.url,
                        base_url=base_url,
                        domain=domain,
                        title=page.title,
                        text_content=page.text_content,
                        content_snippet=page.content_snippet,
                        images=images_json,
                        images_count=len(page.images) if page.images else 0,
                        content_hash=content_hash,
                        word_count=word_count,
                        crawl_status='completed',
                        http_status_code=200,
                        is_processed=True,
                    )
                    db.add(content_manager)
                    stored += 1
                except Exception as e:
                    logger.error(f"Error preparing page {page.url}: {e}")
                    failed += 1
            
            # Commit all at once
            if stored > 0:
                db.commit()
                logger.info(f"Batch storage completed: {stored} stored, {failed} failed")
            
            return {
                "stored": stored,
                "failed": failed,
                "total": len(pages)
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing batch: {e}")
            return {
                "stored": 0,
                "failed": len(pages),
                "total": len(pages)
            }


    @staticmethod
    def get_content_by_id(db: Session, content_id: str) -> Optional[ContentManager]:
        """Retrieve content by UUID"""
        try:
            content = db.query(ContentManager).filter(ContentManager.id == content_id).first()
            return content
        except Exception as e:
            logger.error(f"Error retrieving content by ID {content_id}: {e}")
            return None


# Singleton instance
database_service = DatabaseService()
