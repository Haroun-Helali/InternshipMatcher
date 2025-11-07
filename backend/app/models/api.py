"""
Pydantic models for API requests and responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Document Models
class DocumentMetadataResponse(BaseModel):
    """Document metadata response."""
    
    document_id: str
    filename: str
    file_size: int
    page_count: int
    document_type: str
    created_at: datetime
    chunk_count: int


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    
    success: bool
    message: str
    document_id: str
    filename: str
    chunks_created: int
    task_id: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    
    documents: List[DocumentMetadataResponse]
    total_count: int


class DocumentStatsResponse(BaseModel):
    """Knowledge base statistics."""
    
    total_documents: int
    total_chunks: int
    total_size_bytes: int
    average_chunks_per_document: float


# Query Models
class QueryRequest(BaseModel):
    """Request for RAG query."""
    
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class SourceReference(BaseModel):
    """Source document reference."""
    
    source_file: str
    page_number: int
    document_id: str
    content_preview: str


class QueryResponse(BaseModel):
    """Response for RAG query."""
    
    answer: str
    sources: List[SourceReference]
    query: str
    model: str
    session_id: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Conversation history response."""
    
    session_id: str
    turns: List[Dict[str, str]]
    turn_count: int


# Health & Status Models
class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    services: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Error response."""
    
    error: str
    detail: Optional[str] = None
    status_code: int
