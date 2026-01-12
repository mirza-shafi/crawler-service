"""
Database Models - SQLAlchemy models for crawled content with pgvector
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class CrawledContent(Base):
    """Model for storing crawled content with embeddings"""
    
    __tablename__ = "crawled_content"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=True)
    text_content = Column(Text, nullable=False)
    content_snippet = Column(Text, nullable=True)
    base_url = Column(String(512), nullable=False, index=True)
    images_count = Column(Integer, default=0)
    crawl_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Vector embedding column (384 dimensions for all-MiniLM-L6-v2)
    embedding = Column(Vector(384), nullable=True)
    
    # Create index for vector similarity search
    __table_args__ = (
        Index(
            'idx_embedding_vector',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )
    
    def __repr__(self):
        return f"<CrawledContent(url='{self.url}', title='{self.title}')>"
