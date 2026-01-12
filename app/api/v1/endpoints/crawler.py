"""
Crawler Endpoints - FastAPI routes for crawling operations
"""

import logging
from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Form

from ....schemas.crawler import CrawlRequest, CrawlResponse, CrawlErrorResponse
from ....services.crawler import crawler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawler")


@router.get("/health", status_code=200)
async def health_check():
    """
    Health check endpoint

    Returns:
        Status of the crawler service
    """
    return {"status": "healthy", "service": "crawler-microservice"}


@router.post(
    "/crawl",
    response_model=CrawlResponse,
    status_code=200,
    responses={
        400: {"model": CrawlErrorResponse, "description": "Invalid input"},
        500: {"model": CrawlErrorResponse, "description": "Internal server error"},
    },
)
async def crawl(
    seed_url: Annotated[str, Form(description="Starting URL to crawl (e.g., https://example.com)", examples=["https://example.com"])],
    max_pages: Annotated[int, Form(description="Maximum number of pages to crawl (1-500)", ge=1, le=500)] = 10,
    follow_external_links: Annotated[bool, Form(description="Follow links outside the base domain")] = False,
) -> CrawlResponse:
    """
    Crawl and scrape a website

    ## Description
    Crawls a website starting from a seed URL, following internal links
    within the same domain. Extracts page titles, content, and image URLs.

    ## Parameters
    - **seed_url**: The starting URL to begin crawling
    - **max_pages**: Maximum number of pages to crawl (1-500, default: 10)
    - **follow_external_links**: Whether to follow links outside the base domain (default: false)

    ## Returns
    A structured response containing:
    - All crawled pages with their content and images
    - Total pages crawled and requested
    - Any errors encountered during crawling
    - Total crawl duration in seconds
    """
    try:
        logger.info(f"Crawl request: {seed_url} (max_pages={max_pages})")

        # Perform the crawl
        result = await crawler_service.crawl(
            seed_url=seed_url,
            max_pages=max_pages,
            follow_external_links=follow_external_links,
        )

        logger.info(f"Crawl completed successfully: {result.total_pages_crawled} pages")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during crawl: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during crawling",
        )


@router.post("/crawl/batch", response_model=dict, status_code=200)
async def crawl_batch(requests: list[CrawlRequest]) -> dict:
    """
    Batch crawl multiple websites

    ## Description
    Crawl multiple websites sequentially. Each crawl is performed
    independently with its own domain boundary.

    ## Parameters
    - **requests**: List of CrawlRequest objects

    ## Returns
    Dictionary containing results for each URL with crawl status
    """
    if not requests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one crawl request is required",
        )

    if len(requests) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 URLs per batch request",
        )

    results = {}

    try:
        for idx, request in enumerate(requests):
            try:
                logger.info(
                    f"Batch crawl {idx + 1}/{len(requests)}: {request.seed_url}"
                )

                result = await crawler_service.crawl(
                    seed_url=str(request.seed_url),
                    max_pages=request.max_pages,
                    follow_external_links=request.follow_external_links,
                )

                results[str(request.seed_url)] = {
                    "success": True,
                    "data": result.model_dump(),
                }
            except Exception as e:
                logger.error(f"Error crawling {request.seed_url}: {str(e)}")
                results[str(request.seed_url)] = {
                    "success": False,
                    "error": str(e),
                }

        return {"batch_results": results}

    except Exception as e:
        logger.error(f"Unexpected error during batch crawl: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during batch crawling",
        )
