"""Document processing service following SOLID principles.

This module handles PDF text extraction, cleaning, and chunking for RAG.
"""
import re
import uuid
from pathlib import Path
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader

from backend.app.core.config import get_settings
from backend.app.core.exceptions import DocumentProcessingError
from backend.app.core.logging import get_logger
from backend.app.models.document import (
    DocumentChunk,
    DocumentMetadata,
    ProcessedDocument,
)

logger = get_logger(__name__)


class DocumentProcessor:
    """Handles document processing operations.

    Implements Single Responsibility Principle - only processes documents.
    """

    def __init__(self):
        """Initialize document processor with configuration."""
        self.settings = get_settings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def process_pdf(
        self,
        file_path: Path,
        custom_metadata: Optional[dict] = None,
        document_id: Optional[str] = None,
    ) -> ProcessedDocument:
        """Process a PDF file and return structured document with chunks.

        Args:
            file_path: Path to the PDF file
            custom_metadata: Optional custom metadata to attach
            document_id: Optional pre-assigned document ID. When the caller
                (e.g. the upload endpoint) already generated an ID and handed
                it back to the client, pass it here so the rest of the
                pipeline (vector store, listings) uses the same value.
                Generates a new UUID when None.

        Returns:
            ProcessedDocument with all chunks and metadata

        Raises:
            DocumentProcessingError: If PDF processing fails
        """
        logger.info(f"Processing PDF: {file_path.name}")

        try:
            # Extract text from PDF
            text, page_count = self._extract_text_from_pdf(file_path)

            # Clean the text
            cleaned_text = self._clean_text(text)

            # Create metadata
            metadata = self._create_metadata(
                file_path=file_path,
                page_count=page_count,
                document_type="pdf",
                custom_metadata=custom_metadata
            )

            # Chunk the text
            chunks = self._chunk_text(cleaned_text, metadata)

            # Create processed document
            doc_id = document_id or str(uuid.uuid4())
            processed_doc = ProcessedDocument(
                document_id=doc_id,
                metadata=metadata,
                chunks=chunks,
                total_chunks=len(chunks)
            )

            logger.info(
                f"Successfully processed {file_path.name}: "
                f"{len(chunks)} chunks created"
            )

            return processed_doc

        except Exception as e:
            logger.error(f"Failed to process PDF {file_path.name}: {e}", exc_info=True)
            raise DocumentProcessingError(
                message=f"Failed to process PDF: {file_path.name}",
                details={"error": str(e), "file": str(file_path)}
            ) from e

    def _extract_text_from_pdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, page_count)

        Raises:
            Exception: If PDF reading fails
        """
        try:
            reader = PdfReader(str(file_path))
            page_count = len(reader.pages)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()

                if page_text.strip():
                    text_parts.append(f"[Page {page_num}]\n{page_text}")
                else:
                    logger.warning(
                        f"Page {page_num} of {file_path.name} has no extractable text"
                    )

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                raise ValueError("No extractable text found in PDF")

            logger.debug(f"Extracted {len(full_text)} characters from {page_count} pages")

            return full_text, page_count

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)

        # Remove page markers but keep the content
        text = re.sub(r'\[Page \d+\]\s*', '', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _create_metadata(
        self,
        file_path: Path,
        page_count: int,
        document_type: str,
        custom_metadata: Optional[dict] = None
    ) -> DocumentMetadata:
        """Create document metadata.

        Args:
            file_path: Path to the file
            page_count: Number of pages in document
            document_type: Type of document (pdf, docx)
            custom_metadata: Optional custom metadata

        Returns:
            DocumentMetadata object
        """
        return DocumentMetadata(
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            page_count=page_count,
            document_type=document_type,
            custom_metadata=custom_metadata or {}
        )

    def _chunk_text(
        self,
        text: str,
        metadata: DocumentMetadata
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk
            metadata: Document metadata to attach to each chunk

        Returns:
            List of DocumentChunk objects
        """
        # Use LangChain's text splitter
        text_chunks = self.text_splitter.split_text(text)

        # Create DocumentChunk objects
        chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                content=chunk_text.strip(),
                chunk_index=idx,
                start_page=None,  # TODO: Track page numbers in future enhancement
                end_page=None,
                metadata=metadata
            )
            chunks.append(chunk)

        logger.debug(f"Created {len(chunks)} chunks from text")

        return chunks

    def validate_file(self, file_path: Path) -> bool:
        """Validate that file exists and is processable.

        Args:
            file_path: Path to file

        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False

        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            return False

        if file_path.stat().st_size > self.settings.max_file_size_bytes:
            logger.error(
                f"File too large: {file_path.stat().st_size} bytes "
                f"(max: {self.settings.max_file_size_bytes})"
            )
            return False

        if file_path.suffix.lower() not in ['.pdf']:
            logger.error(f"Unsupported file type: {file_path.suffix}")
            return False

        return True


# Factory function for dependency injection
def get_document_processor() -> DocumentProcessor:
    """Get DocumentProcessor instance.

    Follows Dependency Inversion Principle for easy testing.
    """
    return DocumentProcessor()
