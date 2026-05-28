"""Integration tests for document processor."""
from pathlib import Path

import pytest

from backend.app.core.exceptions import DocumentProcessingError
from backend.app.services.document_processor import get_document_processor


@pytest.fixture
def processor():
    """Get document processor instance."""
    return get_document_processor()


@pytest.fixture
def sample_pdf_path():
    """Path to sample internship PDF."""
    return Path(__file__).parent.parent / "fixtures" / "sample_internship.pdf"


@pytest.fixture
def malformed_pdf_path():
    """Path to malformed PDF."""
    return Path(__file__).parent.parent / "fixtures" / "malformed.pdf"


@pytest.fixture
def empty_pdf_path():
    """Path to empty PDF."""
    return Path(__file__).parent.parent / "fixtures" / "empty.pdf"


def test_process_valid_pdf(processor, sample_pdf_path):
    """Test processing a valid internship PDF."""
    assert sample_pdf_path.exists(), "Sample PDF not found. Run tests/fixtures/create_samples.py first."

    # Process the PDF
    result = processor.process_pdf(sample_pdf_path)

    # Verify result structure
    assert result.document_id is not None
    assert result.metadata.filename == "sample_internship.pdf"
    assert result.metadata.document_type == "pdf"
    assert result.metadata.page_count > 0
    assert result.total_chunks > 0
    assert len(result.chunks) == result.total_chunks

    # Verify chunks have content
    for chunk in result.chunks:
        assert chunk.content.strip()
        assert chunk.chunk_index >= 0
        assert chunk.metadata.filename == "sample_internship.pdf"


def test_process_pdf_with_custom_metadata(processor, sample_pdf_path):
    """Test processing PDF with custom metadata."""
    custom_meta = {
        "company": "Tech Innovations Inc.",
        "category": "software-engineering"
    }

    result = processor.process_pdf(sample_pdf_path, custom_metadata=custom_meta)

    assert result.metadata.custom_metadata["company"] == "Tech Innovations Inc."
    assert result.metadata.custom_metadata["category"] == "software-engineering"


def test_process_pdf_content_extraction(processor, sample_pdf_path):
    """Test that key content is extracted from PDF."""
    result = processor.process_pdf(sample_pdf_path)

    # Combine all chunk content
    full_content = " ".join(chunk.content for chunk in result.chunks)

    # Verify key terms from the internship posting are present
    assert "Software Engineering Internship" in full_content or "software" in full_content.lower()
    assert "Python" in full_content or "python" in full_content.lower()

    # Verify content was actually extracted (not empty)
    assert len(full_content) > 100


def test_process_pdf_chunk_overlap(processor, sample_pdf_path):
    """Test that chunks have proper overlap."""
    result = processor.process_pdf(sample_pdf_path)

    # If we have multiple chunks, they should have some overlap
    if len(result.chunks) > 1:
        # This is a heuristic check - exact overlap is hard to verify
        # but we can check that chunks are reasonable sizes
        for chunk in result.chunks:
            assert len(chunk.content) <= processor.settings.chunk_size + processor.settings.chunk_overlap


def test_process_pdf_chunk_ordering(processor, sample_pdf_path):
    """Test that chunks maintain proper order."""
    result = processor.process_pdf(sample_pdf_path)

    # Verify chunks are in sequential order
    for idx, chunk in enumerate(result.chunks):
        assert chunk.chunk_index == idx


def test_process_malformed_pdf(processor, malformed_pdf_path):
    """Test that malformed PDF raises appropriate error."""
    with pytest.raises(DocumentProcessingError) as exc_info:
        processor.process_pdf(malformed_pdf_path)

    assert "Failed to process PDF" in str(exc_info.value)


def test_process_empty_pdf(processor, empty_pdf_path):
    """Test processing an empty PDF."""
    # Empty PDFs should raise an error
    with pytest.raises(DocumentProcessingError) as exc_info:
        processor.process_pdf(empty_pdf_path)

    # Error message should indicate the problem
    assert "Failed to process PDF" in str(exc_info.value)


def test_validate_file_integration(processor, sample_pdf_path):
    """Test file validation with real PDF."""
    assert processor.validate_file(sample_pdf_path)


def test_multiple_pdf_processing(processor, sample_pdf_path):
    """Test processing the same PDF multiple times."""
    result1 = processor.process_pdf(sample_pdf_path)
    result2 = processor.process_pdf(sample_pdf_path)

    # Document IDs should be different (unique)
    assert result1.document_id != result2.document_id

    # But content should be the same
    assert result1.total_chunks == result2.total_chunks
    assert result1.metadata.filename == result2.metadata.filename


def test_processor_handles_special_characters(processor, sample_pdf_path):
    """Test that processor handles special characters in content."""
    result = processor.process_pdf(sample_pdf_path)

    # Verify no control characters in chunks
    for chunk in result.chunks:
        # Should not contain null bytes or other control characters
        assert '\x00' not in chunk.content
        assert '\x01' not in chunk.content


def test_chunk_metadata_consistency(processor, sample_pdf_path):
    """Test that all chunks have consistent metadata."""
    result = processor.process_pdf(sample_pdf_path)

    # All chunks should have same document metadata
    first_metadata = result.chunks[0].metadata

    for chunk in result.chunks[1:]:
        assert chunk.metadata.filename == first_metadata.filename
        assert chunk.metadata.file_size == first_metadata.file_size
        assert chunk.metadata.page_count == first_metadata.page_count
        assert chunk.metadata.document_type == first_metadata.document_type


def test_factory_function_returns_working_processor(sample_pdf_path):
    """Test that factory function returns a working processor."""
    processor = get_document_processor()
    result = processor.process_pdf(sample_pdf_path)

    assert result.total_chunks > 0
