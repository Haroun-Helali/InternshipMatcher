"""Custom exceptions following Open/Closed Principle."""
from typing import Any, Dict, Optional


class RAGApplicationError(Exception):
    """Base exception for all application errors.

    Provides consistent error handling across the application.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class DocumentProcessingError(RAGApplicationError):
    """Raised when document processing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=422)


class EmbeddingError(RAGApplicationError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=503)


class VectorStoreError(RAGApplicationError):
    """Raised when vector store operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=500)


class RAGPipelineError(RAGApplicationError):
    """Raised when RAG pipeline execution fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=500)


class LLMError(RAGApplicationError):
    """Raised when LLM operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=503)


class ValidationError(RAGApplicationError):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=400)


class NotFoundError(RAGApplicationError):
    """Raised when a resource is not found."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, status_code=404)
