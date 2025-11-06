"""Document models for request/response schemas."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for a processed document."""
    
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(default_factory=datetime.now)
    page_count: Optional[int] = Field(None, description="Number of pages (for PDFs)")
    document_type: str = Field(..., description="Type of document (pdf, docx)")
    custom_metadata: Dict[str, str] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A chunk of text from a document with metadata."""
    
    content: str = Field(..., description="Text content of the chunk")
    chunk_index: int = Field(..., description="Index of this chunk in the document")
    start_page: Optional[int] = Field(None, description="Starting page number")
    end_page: Optional[int] = Field(None, description="Ending page number")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Sample internship description...",
                "chunk_index": 0,
                "start_page": 1,
                "end_page": 1,
                "metadata": {
                    "filename": "internship.pdf",
                    "file_size": 12345,
                    "page_count": 1,
                    "document_type": "pdf"
                }
            }
        }


class ProcessedDocument(BaseModel):
    """A fully processed document with all chunks."""
    
    document_id: str = Field(..., description="Unique document identifier")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    chunks: List[DocumentChunk] = Field(..., description="List of text chunks")
    total_chunks: int = Field(..., description="Total number of chunks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc-123",
                "metadata": {
                    "filename": "internship.pdf",
                    "file_size": 12345,
                    "page_count": 3,
                    "document_type": "pdf"
                },
                "chunks": [],
                "total_chunks": 5
            }
        }


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    chunks_created: int = Field(..., description="Number of chunks created")
