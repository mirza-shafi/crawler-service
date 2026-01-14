"""
Configuration Module - Application Settings

Handles environment variables and configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application settings
    APP_NAME: str = "Crawler Microservice"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Crawler settings
    MAX_CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT: int = 30  # seconds
    DEFAULT_MAX_PAGES: int = 50
    MAX_ALLOWED_PAGES: int = 500

    # HTTP Client settings
    USER_AGENT: str = "CrawlerBot/1.0 (Compatible with ApifyBot)"
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # seconds

    # Content extraction settings
    CONTENT_SNIPPET_LENGTH: int = 200  # characters
    MAX_CONTENT_LENGTH: int = 10000  # characters per page
    
    # Database settings
    DATABASE_URL: str = ""
    VECTOR_STORAGE_ENABLED: bool = False
    
    # Redis settings
    REDIS_URL: str = "redis://redis:6379"
    
    # Embedding settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    # File upload settings
    MAX_FILE_SIZE_MB: int = 50  # Maximum file size in MB
    ALLOWED_FILE_TYPES: list = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "text/html"
    ]
    UPLOAD_DIR: str = "uploads"  # Directory for temporary file storage

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
