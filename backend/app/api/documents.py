"""Document management API endpoints."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.models.api import (
    DocumentListResponse,
    DocumentMetadataResponse,
    DocumentStatsResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from backend.app.services.document_processor import get_document_processor
from backend.app.services.document_store import get_document_store
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()

# Initialize services. The document store is fetched lazily inside each
# handler so tests can swap in a tmpdir-backed SQLite before the first call.
doc_processor = get_document_processor()
embedding_service = get_embedding_service()
vector_store = get_vector_store()


async def process_document_background(
    file_path: Path, document_id: str, filename: str
) -> None:
    """Background task to process document and generate embeddings.

    The status transitions are written to the SQLite store so a poll on
    `/documents/{id}/status` reflects reality even after a backend restart.
    """
    try:
        logger.info(f"Starting background processing for {filename}")
        get_document_store().mark_processing(document_id)

        # Process PDF — pass the upload-side document_id so it threads through
        # to chunks, the vector store, and the listing.
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

        # Persist metadata + final READY state in a single update.
        get_document_store().mark_ready(
            processed_doc.document_id,
            file_size=processed_doc.metadata.file_size,
            page_count=processed_doc.metadata.page_count,
            document_type=processed_doc.metadata.document_type,
            chunk_count=len(processed_doc.chunks),
            created_at=processed_doc.metadata.upload_date.isoformat(),
        )
        logger.info(
            f"Successfully processed {filename}: {len(processed_doc.chunks)} chunks"
        )

    except Exception as e:
        logger.error(f"Background processing failed for {filename}: {e}", exc_info=True)
        get_document_store().mark_failed(document_id, error=str(e))


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """Upload and process a PDF document.

    The document is processed in the background: extract text → split into
    chunks → generate embeddings → store in the vector database. Poll
    `/documents/{id}/status` for progress.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        document_id = str(uuid.uuid4())

        content = await file.read()
        logger.info(f"Uploading file: {file.filename} ({len(content)} bytes)")

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(exist_ok=True)

        temp_file_path = upload_dir / f"{document_id}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        logger.info(f"Uploaded file saved: {temp_file_path}")

        # Persist the pending state immediately so a status poll right after
        # /upload returns something useful instead of 404.
        get_document_store().insert_pending(document_id, file.filename)

        background_tasks.add_task(
            process_document_background, temp_file_path, document_id, file.filename
        )

        return DocumentUploadResponse(
            success=True,
            message="Document uploaded successfully. Processing in background.",
            document_id=document_id,
            filename=file.filename,
            chunks_created=0,
            task_id=document_id,
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to upload document: {str(e)}"
        ) from e


@router.get("/", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List every fully-processed document. In-flight uploads are not included.

    Use `/documents/{id}/status` to inspect documents that are still being
    indexed.
    """
    try:
        rows = get_document_store().list_ready_metadata()
        documents = [DocumentMetadataResponse(**row) for row in rows]
        return DocumentListResponse(documents=documents, total_count=len(documents))
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve document list"
        ) from e


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    """Delete a document and all its chunks."""
    try:
        if not get_document_store().exists(document_id):
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        deleted_count = vector_store.delete_document(document_id)
        status_before = get_document_store().get_status(document_id)
        filename = status_before["filename"] if status_before else "unknown"
        get_document_store().delete(document_id)

        logger.info(
            f"Deleted document {document_id}: {deleted_count} chunks removed"
        )
        return {
            "success": True,
            "message": f"Document '{filename}' deleted successfully",
            "document_id": document_id,
            "chunks_deleted": deleted_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {str(e)}"
        ) from e


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str) -> DocumentStatusResponse:
    """Return the current lifecycle state of an uploaded document.

    Frontends should poll this after /upload to know when the doc is queryable
    (state == ready) or whether processing failed (state == failed, with
    `error` populated).
    """
    status = get_document_store().get_status(document_id)
    if status is None:
        raise HTTPException(
            status_code=404, detail=f"No status for document {document_id}"
        )
    return DocumentStatusResponse(**status)


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_stats() -> DocumentStatsResponse:
    """Aggregate counts and storage for ready documents."""
    try:
        stats = get_document_store().stats()
        # Cross-check against the vector store; chroma is the source of truth
        # for chunk count when they disagree (e.g. orphaned chunks from a
        # previous run before SQLite existed).
        chroma_chunks = vector_store.get_document_count()
        total_chunks = max(stats["total_chunks"], chroma_chunks)
        total_documents = stats["total_documents"]
        avg_chunks = total_chunks / total_documents if total_documents > 0 else 0

        return DocumentStatsResponse(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_size_bytes=stats["total_size_bytes"],
            average_chunks_per_document=avg_chunks,
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve statistics"
        ) from e
