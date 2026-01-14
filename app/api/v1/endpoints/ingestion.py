"""
Ingestion Endpoints - API routes for file upload, text input, and batch operations
"""

import logging
from typing import Annotated, Optional, List
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ....schemas.ingestion import (
    TextIngestionRequest,
    FileUploadResponse,
    BatchUploadResponse,
    ContentListResponse,
    ContentListItem
)
from ....services.content_ingestion import content_ingestion_service
from ....models.content_manager import ContentManager
from ....core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion")


@router.post(
    "/upload/file",
    response_model=FileUploadResponse,
    status_code=200,
    summary="Upload a file for content ingestion",
    description="""
    Upload a file (PDF, DOCX, TXT, MD, HTML) for text extraction and indexing.
    
    The file will be processed to extract text content, generate embeddings (if enabled),
    and store in the content_manager database for semantic search.
    
    **Supported formats:**
    - PDF (.pdf)
    - Microsoft Word (.docx)
    - Plain text (.txt)
    - Markdown (.md)
    - HTML (.html, .htm)
    
    **Maximum file size:** 50MB (configurable)
    """
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    title: Annotated[Optional[str], Form(description="Optional title for the content")] = None,
    db: Session = Depends(get_db)
) -> FileUploadResponse:
    """
    Upload and process a single file
    
    Args:
        file: Uploaded file
        title: Optional title
        db: Database session
        
    Returns:
        FileUploadResponse with processing results
    """
    try:
        logger.info(f"File upload request: {file.filename}")
        
        # Ingest the file
        content = await content_ingestion_service.ingest_file(
            file=file,
            db=db,
            title=title
        )
        
        return FileUploadResponse(
            success=True,
            content_id=str(content.id),
            filename=file.filename,
            source_type=content.source_type,
            mime_type=content.content_type,
            word_count=content.word_count,
            embedding_generated=content.embedding is not None,
            message="File processed successfully"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )


@router.post(
    "/upload/text",
    response_model=FileUploadResponse,
    status_code=200,
    summary="Ingest raw text content",
    description="""
    Ingest raw text content directly via API.
    
    This endpoint allows you to submit text content without uploading a file.
    The text will be processed, indexed, and made searchable via semantic search.
    
    **Use cases:**
    - Programmatic content ingestion
    - Copy-paste text from other sources
    - Integration with other systems
    """
)
async def upload_text(
    request: TextIngestionRequest,
    db: Session = Depends(get_db)
) -> FileUploadResponse:
    """
    Ingest raw text content
    
    Args:
        request: Text ingestion request
        db: Database session
        
    Returns:
        FileUploadResponse with processing results
    """
    try:
        logger.info(f"Text upload request: {request.source_identifier or 'unnamed'}")
        
        # Ingest the text
        content = await content_ingestion_service.ingest_text(
            text_content=request.text_content,
            db=db,
            title=request.title,
            source_identifier=request.source_identifier,
            metadata=request.metadata
        )
        
        return FileUploadResponse(
            success=True,
            content_id=str(content.id),
            filename=content.source_identifier or "text-input",
            source_type=content.source_type,
            mime_type=content.content_type,
            word_count=content.word_count,
            embedding_generated=content.embedding is not None,
            message="Text processed successfully"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing text upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process text: {str(e)}"
        )


@router.post(
    "/upload/batch",
    response_model=BatchUploadResponse,
    status_code=200,
    summary="Upload multiple files in batch",
    description="""
    Upload multiple files at once for batch processing.
    
    All files will be processed independently. If some files fail, others will still
    be processed successfully. The response will include individual results for each file.
    
    **Maximum files per batch:** 10 (configurable)
    **Supported formats:** PDF, DOCX, TXT, MD, HTML
    """
)
async def upload_batch(
    files: List[UploadFile] = File(..., description="List of files to upload"),
    db: Session = Depends(get_db)
) -> BatchUploadResponse:
    """
    Upload and process multiple files in batch
    
    Args:
        files: List of uploaded files
        db: Database session
        
    Returns:
        BatchUploadResponse with batch processing results
    """
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one file is required"
            )
        
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 files per batch request"
            )
        
        logger.info(f"Batch upload request: {len(files)} files")
        
        # Process batch
        result = await content_ingestion_service.ingest_batch(
            files=files,
            db=db
        )
        
        return BatchUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing batch upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch: {str(e)}"
        )


@router.get(
    "/content/list",
    response_model=ContentListResponse,
    status_code=200,
    summary="List ingested content",
    description="""
    List all ingested content with optional filtering by source type.
    
    **Source types:**
    - `url` - Content from web crawling
    - `file` - Content from file uploads
    - `text` - Content from direct text input
    
    Results are paginated using limit and offset parameters.
    """
)
async def list_content(
    source_type: Annotated[Optional[str], "Filter by source type (url, file, text)"] = None,
    limit: Annotated[int, "Maximum number of items to return"] = 50,
    offset: Annotated[int, "Number of items to skip"] = 0,
    db: Session = Depends(get_db)
) -> ContentListResponse:
    """
    List ingested content with pagination
    
    Args:
        source_type: Optional filter by source type
        limit: Maximum items to return
        offset: Number of items to skip
        db: Database session
        
    Returns:
        ContentListResponse with content items
    """
    try:
        # Build query
        query = select(ContentManager)
        
        # Apply source type filter
        if source_type:
            query = query.where(ContentManager.source_type == source_type)
        
        # Get total count
        count_query = select(func.count()).select_from(ContentManager)
        if source_type:
            count_query = count_query.where(ContentManager.source_type == source_type)
        total_count = db.execute(count_query).scalar()
        
        # Apply pagination and ordering
        query = query.order_by(ContentManager.crawl_timestamp.desc())
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = db.execute(query)
        contents = result.scalars().all()
        
        # Format items
        items = [
            ContentListItem(
                id=str(content.id),
                source_type=content.source_type,
                source_identifier=content.source_identifier or content.url,
                title=content.title,
                word_count=content.word_count,
                crawl_timestamp=content.crawl_timestamp.isoformat() if content.crawl_timestamp else "",
                is_indexed=content.is_indexed
            )
            for content in contents
        ]
        
        return ContentListResponse(
            success=True,
            total_count=total_count,
            items=items,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list content: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=dict,
    status_code=200,
    summary="Get ingestion statistics",
    description="Get statistics about ingested content by source type"
)
async def get_ingestion_stats(
    db: Session = Depends(get_db)
) -> dict:
    """
    Get statistics about ingested content
    
    Args:
        db: Database session
        
    Returns:
        Dict with statistics by source type
    """
    try:
        # Count by source type
        url_count = db.execute(
            select(func.count()).select_from(ContentManager).where(ContentManager.source_type == 'url')
        ).scalar()
        
        file_count = db.execute(
            select(func.count()).select_from(ContentManager).where(ContentManager.source_type == 'file')
        ).scalar()
        
        text_count = db.execute(
            select(func.count()).select_from(ContentManager).where(ContentManager.source_type == 'text')
        ).scalar()
        
        total_count = db.execute(
            select(func.count()).select_from(ContentManager)
        ).scalar()
        
        indexed_count = db.execute(
            select(func.count()).select_from(ContentManager).where(ContentManager.is_indexed == True)
        ).scalar()
        
        return {
            "total_content": total_count,
            "by_source_type": {
                "url": url_count,
                "file": file_count,
                "text": text_count
            },
            "indexed_content": indexed_count,
            "indexing_percentage": round((indexed_count / total_count * 100) if total_count > 0 else 0, 2)
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
