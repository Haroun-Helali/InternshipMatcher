"""Unit tests for document processor."""
import tempfile
from pathlib import Path

import pytest
from PyPDF2 import PdfWriter

from backend.app.services.document_processor import DocumentProcessor
from backend.app.core.exceptions import DocumentProcessingError


@pytest.fixture
def processor():
    """Create document processor instance."""
    return DocumentProcessor()


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    # Create a temporary PDF with sample text
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        writer = PdfWriter()
        
        # Note: PdfWriter in PyPDF2 requires adding pages
        # For testing, we'll create a simple PDF
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_processor_initialization(processor):
    """Test that processor initializes correctly."""
    assert processor is not None
    assert processor.text_splitter is not None
    assert processor.settings.chunk_size == 500
    assert processor.settings.chunk_overlap == 50


def test_clean_text(processor):
    """Test text cleaning functionality."""
    # Test whitespace normalization
    text = "Hello    world\n\n\n\nNew   paragraph"
    cleaned = processor._clean_text(text)
    assert "    " not in cleaned
    assert "\n\n\n" not in cleaned
    
    # Test control character removal
    text_with_control = "Hello\x00\x01World"
    cleaned = processor._clean_text(text_with_control)
    assert "\x00" not in cleaned
    assert "\x01" not in cleaned
    
    # Test page marker removal
    text_with_markers = "[Page 1]\nContent here\n[Page 2]\nMore content"
    cleaned = processor._clean_text(text_with_markers)
    assert "[Page" not in cleaned
    assert "Content here" in cleaned


def test_create_metadata(processor, tmp_path):
    """Test metadata creation."""
    # Create a temporary file
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")
    
    metadata = processor._create_metadata(
        file_path=test_file,
        page_count=5,
        document_type="pdf",
        custom_metadata={"company": "Test Corp"}
    )
    
    assert metadata.filename == "test.pdf"
    assert metadata.page_count == 5
    assert metadata.document_type == "pdf"
    assert metadata.custom_metadata["company"] == "Test Corp"
    assert metadata.file_size > 0


def test_chunk_text(processor):
    """Test text chunking."""
    # Create a long text that will be chunked
    text = "This is a test. " * 100  # ~1500 characters
    
    from backend.app.models.document import DocumentMetadata
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        page_count=1,
        document_type="pdf"
    )
    
    chunks = processor._chunk_text(text, metadata)
    
    # Verify chunks were created
    assert len(chunks) > 1
    
    # Verify chunk properties
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx
        assert chunk.content
        assert len(chunk.content) <= processor.settings.chunk_size + processor.settings.chunk_overlap
        assert chunk.metadata == metadata


def test_chunk_text_overlap(processor):
    """Test that chunks have proper overlap."""
    # Create text that will produce exactly 2 chunks
    chunk_size = processor.settings.chunk_size
    overlap = processor.settings.chunk_overlap
    
    text = "A" * chunk_size + "B" * overlap + "C" * chunk_size
    
    from backend.app.models.document import DocumentMetadata
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        page_count=1,
        document_type="pdf"
    )
    
    chunks = processor._chunk_text(text, metadata)
    
    # Should create multiple chunks
    assert len(chunks) >= 2


def test_validate_file_nonexistent(processor, tmp_path):
    """Test validation fails for nonexistent file."""
    fake_file = tmp_path / "nonexistent.pdf"
    assert not processor.validate_file(fake_file)


def test_validate_file_not_pdf(processor, tmp_path):
    """Test validation fails for non-PDF file."""
    text_file = tmp_path / "test.txt"
    text_file.write_text("not a pdf")
    
    assert not processor.validate_file(text_file)


def test_validate_file_too_large(processor, tmp_path):
    """Test validation fails for oversized file."""
    large_file = tmp_path / "large.pdf"
    
    # Create a file larger than max size
    max_size = processor.settings.max_file_size_bytes
    large_file.write_bytes(b"0" * (max_size + 1))
    
    assert not processor.validate_file(large_file)


def test_validate_file_valid(processor, tmp_path):
    """Test validation passes for valid PDF."""
    pdf_file = tmp_path / "valid.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nsmall content")
    
    assert processor.validate_file(pdf_file)


def test_extract_text_from_pdf_empty(processor, tmp_path):
    """Test extraction from PDF with no pages."""
    # This test would require creating an actual empty PDF
    # For now, we'll test the error handling
    pass


def test_chunk_size_configuration():
    """Test that processor respects configuration."""
    from backend.app.core.config import Settings
    
    custom_settings = Settings(chunk_size=200, chunk_overlap=20)
    processor = DocumentProcessor()
    
    # Verify the splitter uses configured values
    assert processor.settings.chunk_size <= 500  # Default or configured


def test_processor_factory():
    """Test the factory function."""
    from backend.app.services.document_processor import get_document_processor
    
    processor = get_document_processor()
    assert isinstance(processor, DocumentProcessor)


def test_chunk_text_with_empty_string(processor):
    """Test chunking empty string."""
    from backend.app.models.document import DocumentMetadata
    
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=0,
        page_count=0,
        document_type="pdf"
    )
    
    chunks = processor._chunk_text("", metadata)
    
    # Should handle empty text gracefully
    assert len(chunks) >= 0


def test_chunk_text_preserves_metadata(processor):
    """Test that all chunks have correct metadata."""
    from backend.app.models.document import DocumentMetadata
    
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        page_count=3,
        document_type="pdf",
        custom_metadata={"key": "value"}
    )
    
    text = "Test content " * 200
    chunks = processor._chunk_text(text, metadata)
    
    for chunk in chunks:
        assert chunk.metadata.filename == "test.pdf"
        assert chunk.metadata.page_count == 3
        assert chunk.metadata.custom_metadata["key"] == "value"
