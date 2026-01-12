"""
Database Service - Handles PostgreSQL operations with pgvector for embeddings
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..models.crawled_content import Base, CrawledContent
from ..schemas.crawler import PageContent

logger = logging.getLogger(__name__)


class VectorDatabaseService:
    """Service for storing and searching crawled content with embeddings in PostgreSQL"""
    
    def __init__(self):
        self.enabled = settings.VECTOR_STORAGE_ENABLED and settings.DATABASE_URL
        self.engine = None
        self.async_session_maker = None
        self.model: Optional[SentenceTransformer] = None
        
        if self.enabled:
            try:
                self._initialize()
                logger.info("Vector database service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize vector database: {e}")
                self.enabled = False
    
    def _initialize(self):
        """Initialize database connection and embedding model"""
        # Convert postgres:// to postgresql:// and add asyncpg driver
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Create async engine
        self.engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Create session maker
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Load embedding model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def initialize_database(self):
        """Create tables and enable pgvector extension"""
        if not self.enabled:
            return False
        
        try:
            async with self.engine.begin() as conn:
                # Enable pgvector extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                logger.info("pgvector extension enabled")
                
                # Create tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def _create_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        # Truncate text if too long
        max_chars = 5000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def store_page(self, page: PageContent, base_url: str) -> bool:
        """
        Store a single crawled page with embedding
        
        Args:
            page: PageContent object with crawled data
            base_url: Base URL of the crawl session
            
        Returns:
            bool: Success status
        """
        if not self.enabled:
            logger.debug("Vector storage not enabled, skipping")
            return False
        
        try:
            # Generate embedding
            text_for_embedding = f"{page.title or ''} {page.text_content}".strip()
            if not text_for_embedding:
                logger.warning(f"No text content to embed for {page.url}")
                return False
            
            embedding = self._create_embedding(text_for_embedding)
            
            # Store in database
            async with self.async_session_maker() as session:
                # Check if URL already exists
                result = await session.execute(
                    select(CrawledContent).where(CrawledContent.url == page.url)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    existing.title = page.title
                    existing.text_content = page.text_content
                    existing.content_snippet = page.content_snippet or page.text_content[:200]
                    existing.base_url = base_url
                    existing.images_count = page.images_count
                    existing.crawl_timestamp = datetime.fromisoformat(page.crawl_timestamp.replace('Z', '+00:00'))
                    existing.embedding = embedding
                    logger.info(f"Updated existing page: {page.url}")
                else:
                    # Create new record
                    content = CrawledContent(
                        url=page.url,
                        title=page.title,
                        text_content=page.text_content,
                        content_snippet=page.content_snippet or page.text_content[:200],
                        base_url=base_url,
                        images_count=page.images_count,
                        crawl_timestamp=datetime.fromisoformat(page.crawl_timestamp.replace('Z', '+00:00')),
                        embedding=embedding
                    )
                    session.add(content)
                    logger.info(f"Stored new page: {page.url}")
                
                await session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing page in database: {e}")
            return False
    
    async def store_pages_batch(self, pages: List[PageContent], base_url: str) -> Dict[str, Any]:
        """
        Store multiple pages with embeddings in batch
        
        Args:
            pages: List of PageContent objects
            base_url: Base URL of the crawl session
            
        Returns:
            Dict with storage statistics
        """
        if not self.enabled:
            return {
                "stored": 0,
                "failed": 0,
                "total": len(pages),
                "enabled": False
            }
        
        stored_count = 0
        failed_count = 0
        
        for page in pages:
            success = await self.store_page(page, base_url)
            if success:
                stored_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Batch storage completed: {stored_count} stored, {failed_count} failed")
        
        return {
            "stored": stored_count,
            "failed": failed_count,
            "total": len(pages),
            "enabled": True
        }
    
    async def search_similar(
        self,
        query: str,
        top_k: int = 5,
        base_url_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity
        
        Args:
            query: Search query text
            top_k: Number of results to return
            base_url_filter: Optional filter by base URL
            
        Returns:
            List of matching results with scores
        """
        if not self.enabled:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._create_embedding(query)
            
            async with self.async_session_maker() as session:
                # Build query with vector similarity
                query_stmt = select(
                    CrawledContent,
                    CrawledContent.embedding.cosine_distance(query_embedding).label('distance')
                )
                
                # Add base_url filter if provided
                if base_url_filter:
                    query_stmt = query_stmt.where(CrawledContent.base_url == base_url_filter)
                
                # Order by similarity and limit
                query_stmt = query_stmt.order_by('distance').limit(top_k)
                
                result = await session.execute(query_stmt)
                rows = result.all()
                
                # Format results
                results = []
                for content, distance in rows:
                    # Convert distance to similarity score (1 - distance for cosine)
                    similarity_score = 1 - distance
                    
                    results.append({
                        "id": content.id,
                        "score": float(similarity_score),
                        "url": content.url,
                        "title": content.title,
                        "content_snippet": content.content_snippet,
                        "base_url": content.base_url,
                        "crawl_timestamp": content.crawl_timestamp.isoformat() if content.crawl_timestamp else None,
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Error searching database: {e}")
            return []
    
    async def get_content_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get crawled content by URL"""
        if not self.enabled:
            return None
        
        try:
            async with self.async_session_maker() as session:
                result = await session.execute(
                    select(CrawledContent).where(CrawledContent.url == url)
                )
                content = result.scalar_one_or_none()
                
                if content:
                    return {
                        "id": content.id,
                        "url": content.url,
                        "title": content.title,
                        "text_content": content.text_content,
                        "content_snippet": content.content_snippet,
                        "base_url": content.base_url,
                        "images_count": content.images_count,
                        "crawl_timestamp": content.crawl_timestamp.isoformat() if content.crawl_timestamp else None,
                    }
                
                return None
        except Exception as e:
            logger.error(f"Error getting content by URL: {e}")
            return None
    
    async def delete_by_base_url(self, base_url: str) -> int:
        """Delete all content associated with a base URL"""
        if not self.enabled:
            return 0
        
        try:
            async with self.async_session_maker() as session:
                result = await session.execute(
                    select(CrawledContent).where(CrawledContent.base_url == base_url)
                )
                contents = result.scalars().all()
                count = len(contents)
                
                for content in contents:
                    await session.delete(content)
                
                await session.commit()
                logger.info(f"Deleted {count} records for base_url: {base_url}")
                return count
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            async with self.async_session_maker() as session:
                # Count total records
                result = await session.execute(
                    select(CrawledContent)
                )
                total_count = len(result.scalars().all())
                
                # Count unique base URLs
                result = await session.execute(
                    text("SELECT COUNT(DISTINCT base_url) FROM crawled_content")
                )
                unique_bases = result.scalar()
                
                return {
                    "enabled": True,
                    "total_pages": total_count,
                    "unique_base_urls": unique_bases,
                    "embedding_dimension": settings.EMBEDDING_DIMENSION,
                    "embedding_model": settings.EMBEDDING_MODEL,
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Singleton instance
vector_db_service = VectorDatabaseService()
