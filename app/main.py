"""
Crawler Microservice - Main Application Entry Point

Uses clean layered architecture:
- api/          - HTTP layer (controllers/endpoints)
- core/         - Cross-cutting concerns (config, utilities)
- models/       - ORM and data models
- schemas/      - Pydantic schemas for request/response validation
- services/     - Business logic layer
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.v1 import api_router
from .services.vector_db_service import vector_db_service
from .core.database import init_db

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Crawler Microservice API",
    description="""
    A high-performance web crawler and scraper microservice built with FastAPI.
    
    ## Features
    
    * **Web Crawling** - Recursively crawl websites following internal links
    * **Domain Boundary** - Automatically stay within the same base domain
    * **Content Extraction** - Extract text content, titles, images, and metadata
    * **File Upload** - Upload PDF, DOCX, TXT, MD, HTML files for text extraction
    * **Text Input** - Direct text content ingestion via API
    * **Batch Processing** - Upload multiple files at once
    * **Async Processing** - Concurrent page fetching using asyncio
    * **Error Handling** - Graceful handling of timeouts and HTTP errors
    * **Batch Operations** - Crawl multiple domains in a single request
    * **Structured Output** - JSON-formatted crawl results with metadata
    * **Semantic Search** - Vector-based similarity search using pgvector
    * **Content Management** - Enhanced storage with 35+ fields for comprehensive content tracking
    
    ## Database & Storage
    
    * **Shared Database**: Uses `auth_app_db` on port 5435 (shared with authentication and app services)
    * **Table**: `content_manager` - Enhanced schema following 11labs crawler architecture
    * **Features**: Content quality scoring, deduplication, metadata tracking, vector embeddings
    * **Fields**: URL tracking, domain extraction, word count, content hash, SEO metadata, JSONB storage
    * **Multi-Source**: Supports URLs, files, and text with unified search
    
    ## Architecture
    
    The service follows a clean layered architecture:
    - **API Layer**: FastAPI endpoints with request/response validation
    - **Service Layer**: Business logic for crawling and scraping
    - **Core Layer**: Configuration and utilities
    - **Data Layer**: PostgreSQL with pgvector for semantic search
    
    ## Performance
    
    - Asynchronous HTTP requests for efficient concurrent fetching
    - Configurable concurrency limits to avoid overwhelming servers
    - Timeout handling to prevent hanging requests
    - Automatic retry logic with configurable delays
    - Optimized database indexes for fast queries
    
    ## Usage
    
    ### Web Crawling
    1. **Basic Crawl**: Send a POST request to `/api/v1/crawler/crawl`
    2. **Batch Crawl**: Send multiple URLs to `/api/v1/crawler/crawl/batch`
    
    ### Content Ingestion
    3. **File Upload**: Upload files at `/api/v1/ingestion/upload/file`
    4. **Text Input**: Submit text at `/api/v1/ingestion/upload/text`
    5. **Batch Upload**: Upload multiple files at `/api/v1/ingestion/upload/batch`
    
    ### Search & Management
    6. **Semantic Search**: Search all content at `/api/v1/crawler/search`
    7. **List Content**: View ingested content at `/api/v1/ingestion/content/list`
    8. **Statistics**: Get stats at `/api/v1/ingestion/stats`
    9. **Vector Stats**: Get database statistics at `/api/v1/crawler/vector/stats`
    5. **Health Check**: GET `/api/v1/crawler/health` to verify service status
    
    ## Content Manager Schema
    
    The `content_manager` table includes:
    - **Identity**: id, url, base_url, domain
    - **Content**: title, description, text_content, content_snippet, raw_html
    - **Media**: images, videos, links (JSONB)
    - **SEO**: meta_tags, keywords, author (JSONB)
    - **Quality**: word_count, content_hash, quality_score
    - **Tracking**: crawl_status, crawl_timestamp, is_processed, is_indexed
    - **Vectors**: embedding (384-dim), embedding_model
    - **Metadata**: custom_metadata (JSONB)
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Startup event - run initialization tasks"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Max concurrent requests: {settings.MAX_CONCURRENT_REQUESTS}")
    logger.info(f"Request timeout: {settings.REQUEST_TIMEOUT}s")
    
    # Create uploads directory
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Uploads directory: {settings.UPLOAD_DIR}")
    
    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    
    # Initialize vector database if enabled
    if vector_db_service.enabled:
        logger.info("Initializing vector database with pgvector...")
        success = await vector_db_service.initialize_database()
        if success:
            logger.info("Vector database initialized successfully")
        else:
            logger.warning("Vector database initialization failed")
    else:
        logger.info("Vector storage is disabled")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - cleanup resources"""
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # Close database connections
    if vector_db_service.enabled:
        await vector_db_service.close()
        logger.info("Vector database connections closed")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint - service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/crawler/health",
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/status", tags=["status"])
async def status():
    """Service status endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "config": {
            "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
            "request_timeout": settings.REQUEST_TIMEOUT,
            "default_max_pages": settings.DEFAULT_MAX_PAGES,
            "max_allowed_pages": settings.MAX_ALLOWED_PAGES,
        },
    }
