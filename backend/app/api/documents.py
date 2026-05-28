"""
Document management API endpoints.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from backend.app.models.api import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentStatsResponse,
    DocumentMetadataResponse,
    DocumentStatusResponse,
    DocumentStatusValue,
)
from backend.app.core.config import get_settings
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
documents_metadata: Dict[str, dict] = {}

# Per-document lifecycle state. Populated at /upload and updated by the
# background worker. Survives only as long as the process — Phase B's SQLite
# migration replaces this dict.
documents_status: Dict[str, dict] = {}


def _set_status(
    document_id: str,
    *,
    state: DocumentStatusValue,
    filename: str,
    chunks_indexed: int = 0,
    error: str | None = None,
) -> None:
    documents_status[document_id] = {
        "document_id": document_id,
        "state": state,
        "filename": filename,
        "chunks_indexed": chunks_indexed,
        "error": error,
        "updated_at": datetime.now(timezone.utc),
    }


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
        _set_status(document_id, state=DocumentStatusValue.PROCESSING, filename=filename)

        # Process PDF (reuse the upload-side document_id so the value returned
        # by /documents/upload matches what shows up in listings and queries)
        processed_doc = doc_processor.process_pdf(file_path, document_id=document_id)

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
            "created_at": processed_doc.metadata.upload_date.isoformat(),
            "chunk_count": len(processed_doc.chunks),
        }

        _set_status(
            document_id,
            state=DocumentStatusValue.READY,
            filename=filename,
            chunks_indexed=len(processed_doc.chunks),
        )
        logger.info(
            f"Successfully processed {filename}: {len(processed_doc.chunks)} chunks"
        )

    except Exception as e:
        logger.error(f"Background processing failed for {filename}: {e}", exc_info=True)
        _set_status(
            document_id,
            state=DocumentStatusValue.FAILED,
            filename=filename,
            error=str(e),
        )


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
    
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        
        logger.info(f"Uploading file: {file.filename} ({len(content)} bytes)")
        
        # Save uploaded file temporarily
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        temp_file_path = upload_dir / f"{document_id}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Uploaded file saved: {temp_file_path}")

        # Mark as pending so a status poll right after /upload returns something
        # useful instead of 404. The background worker flips this to PROCESSING
        # → READY/FAILED as it runs.
        _set_status(
            document_id,
            state=DocumentStatusValue.PENDING,
            filename=file.filename,
        )

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
        documents_status.pop(document_id, None)

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


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str) -> DocumentStatusResponse:
    """Return the current lifecycle state of an uploaded document.

    Frontends should poll this after /upload to know when the doc is queryable
    (state == ready) or whether processing failed (state == failed, with
    `error` populated).
    """
    status = documents_status.get(document_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"No status for document {document_id}",
        )
    return DocumentStatusResponse(**status)


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
