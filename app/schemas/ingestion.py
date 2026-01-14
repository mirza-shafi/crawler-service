"""
Ingestion Schemas - Pydantic models for file upload, text input, and batch operations
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TextIngestionRequest(BaseModel):
    """Schema for text content ingestion"""
    
    text_content: str = Field(..., description="Raw text content to ingest", min_length=1)
    title: Optional[str] = Field(None, description="Title of the content")
    source_identifier: Optional[str] = Field(None, description="Unique identifier for this text (e.g., document ID)")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text_content": "This is a sample document with important information about our product.",
                    "title": "Product Information",
                    "source_identifier": "doc-001",
                    "metadata": {"category": "documentation", "author": "John Doe"}
                }
            ]
        }
    }


class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    
    success: bool = Field(..., description="Whether the upload was successful")
    content_id: str = Field(..., description="UUID of the stored content")
    filename: str = Field(..., description="Original filename")
    source_type: str = Field(..., description="Type of source (file, text, etc.)")
    mime_type: str = Field(..., description="MIME type of the file")
    word_count: int = Field(..., description="Number of words extracted")
    embedding_generated: bool = Field(..., description="Whether vector embedding was generated")
    message: Optional[str] = Field(None, description="Additional message or error details")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "content_id": "123e4567-e89b-12d3-a456-426614174000",
                    "filename": "document.pdf",
                    "source_type": "file",
                    "mime_type": "application/pdf",
                    "word_count": 1234,
                    "embedding_generated": True,
                    "message": "File processed successfully"
                }
            ]
        }
    }


class BatchUploadResponse(BaseModel):
    """Schema for batch upload response"""
    
    success: bool = Field(..., description="Whether the batch operation was successful")
    total_files: int = Field(..., description="Total number of files in the batch")
    successful: int = Field(..., description="Number of successfully processed files")
    failed: int = Field(..., description="Number of failed files")
    results: List[FileUploadResponse] = Field(default=[], description="Individual results for each file")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "total_files": 3,
                    "successful": 2,
                    "failed": 1,
                    "results": []
                }
            ]
        }
    }


class ContentListItem(BaseModel):
    """Schema for content list item"""
    
    id: str = Field(..., description="Content ID")
    source_type: str = Field(..., description="Source type (url, file, text)")
    source_identifier: Optional[str] = Field(None, description="Source identifier (filename, URL, etc.)")
    title: Optional[str] = Field(None, description="Content title")
    word_count: int = Field(..., description="Word count")
    crawl_timestamp: str = Field(..., description="When the content was ingested")
    is_indexed: bool = Field(..., description="Whether content is indexed for search")


class ContentListResponse(BaseModel):
    """Schema for content list response"""
    
    success: bool = Field(default=True, description="Whether the request was successful")
    total_count: int = Field(..., description="Total number of content items")
    items: List[ContentListItem] = Field(default=[], description="List of content items")
    limit: int = Field(..., description="Limit used for pagination")
    offset: int = Field(..., description="Offset used for pagination")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "total_count": 100,
                    "items": [],
                    "limit": 50,
                    "offset": 0
                }
            ]
        }
    }
