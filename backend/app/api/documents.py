"""
Document management API endpoints.
"""

import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pathlib import Path
import uuid
import shutil

from backend.app.models.api import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentStatsResponse,
    DocumentMetadataResponse,
)
from backend.app.core.config import get_settings
from backend.app.core.exceptions import DocumentProcessingError, VectorStoreError
from backend.app.services.document_processor import get_document_processor
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()

# Initialize services
doc_processor = get_document_processor()
embedding_service = get_embedding_service()
vector_store = get_vector_store()

# In-memory storage for document metadata (in production, use a database)
documents_metadata = {}


async def process_document_background(
    file_path: Path, document_id: str, filename: str
) -> None:
    """
    Background task to process document and generate embeddings.
    
    Args:
        file_path: Path to uploaded file
        document_id: Unique document identifier
        filename: Original filename
    """
    try:
        logger.info(f"Starting background processing for {filename}")
        
        # Process PDF
        processed_doc = doc_processor.process_pdf(file_path)
        
        # Generate embeddings
        texts = [chunk.content for chunk in processed_doc.chunks]
        embeddings = await embedding_service.generate_embeddings_batch(
            texts, batch_size=5
        )
        
        # Add to vector store
        vector_store.add_documents(
            processed_doc.chunks, embeddings, processed_doc.document_id
        )
        
        # Store metadata
        documents_metadata[processed_doc.document_id] = {
            "document_id": processed_doc.document_id,
            "filename": filename,
            "file_size": processed_doc.metadata.file_size,
            "page_count": processed_doc.metadata.page_count,
            "document_type": processed_doc.metadata.document_type,
            "created_at": processed_doc.metadata.created_at,
            "chunk_count": len(processed_doc.chunks),
        }
        
        logger.info(
            f"Successfully processed {filename}: {len(processed_doc.chunks)} chunks"
        )
        
    except Exception as e:
        logger.error(f"Background processing failed for {filename}: {e}", exc_info=True)
        # In production, update task status in database
    finally:
        # Cleanup temporary file
        if file_path.exists():
            file_path.unlink()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """
    Upload and process a PDF document.
    
    The document will be processed in the background:
    1. Extract text from PDF
    2. Split into chunks
    3. Generate embeddings
    4. Store in vector database
    
    Args:
        file: PDF file to upload
        background_tasks: FastAPI background tasks
        
    Returns:
        Upload response with document ID and task ID
        
    Raises:
        HTTPException: If upload or validation fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Validate file size
    max_size = settings.max_file_size_bytes
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        )
    
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        temp_file_path = upload_dir / f"{document_id}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Uploaded file saved: {temp_file_path}")
        
        # Process document in background
        background_tasks.add_task(
            process_document_background,
            temp_file_path,
            document_id,
            file.filename
        )
        
        return DocumentUploadResponse(
            success=True,
            message="Document uploaded successfully. Processing in background.",
            document_id=document_id,
            filename=file.filename,
            chunks_created=0,  # Will be updated after processing
            task_id=document_id  # Using document_id as task_id for simplicity
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    List all indexed documents.
    
    Returns:
        List of document metadata
    """
    try:
        documents = [
            DocumentMetadataResponse(**meta)
            for meta in documents_metadata.values()
        ]
        
        return DocumentListResponse(
            documents=documents,
            total_count=len(documents)
        )
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document list"
        )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    """
    Delete a document from the knowledge base.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Success message with deletion count
        
    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        # Check if document exists
        if document_id not in documents_metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        # Delete from vector store
        deleted_count = vector_store.delete_document(document_id)
        
        # Remove from metadata
        filename = documents_metadata[document_id]["filename"]
        del documents_metadata[document_id]
        
        logger.info(f"Deleted document {document_id}: {deleted_count} chunks removed")
        
        return {
            "success": True,
            "message": f"Document '{filename}' deleted successfully",
            "document_id": document_id,
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_stats() -> DocumentStatsResponse:
    """
    Get knowledge base statistics.
    
    Returns:
        Statistics about indexed documents
    """
    try:
        total_documents = len(documents_metadata)
        total_chunks = vector_store.get_document_count()
        
        total_size = sum(
            meta["file_size"] for meta in documents_metadata.values()
        )
        
        avg_chunks = (
            total_chunks / total_documents if total_documents > 0 else 0
        )
        
        return DocumentStatsResponse(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_size_bytes=total_size,
            average_chunks_per_document=avg_chunks
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics"
        )
