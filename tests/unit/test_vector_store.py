"""Unit tests for vector store."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.vector_store import VectorStore, get_vector_store
from backend.app.core.exceptions import VectorStoreError
from backend.app.models.document import DocumentChunk, DocumentMetadata


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        yield mock_client, mock_collection


@pytest.fixture
def vector_store(mock_chromadb, tmp_path):
    """Create vector store with mocked ChromaDB."""
    with patch('backend.app.services.vector_store.get_settings') as mock_settings:
        settings = MagicMock()
        settings.chroma_persist_directory = str(tmp_path / "chroma_data")
        settings.chroma_collection_name = "test_collection"
        settings.top_k_results = 5
        mock_settings.return_value = settings
        
        store = VectorStore()
        return store


def test_vector_store_initialization(vector_store):
    """Test that vector store initializes correctly."""
    assert vector_store.collection is not None
    assert vector_store.client is not None


def test_add_documents_success(vector_store):
    """Test adding documents to vector store."""
    # Create sample chunks
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        page_count=1,
        document_type="pdf"
    )
    
    chunks = [
        DocumentChunk(
            content="Test content 1",
            chunk_index=0,
            metadata=metadata
        ),
        DocumentChunk(
            content="Test content 2",
            chunk_index=1,
            metadata=metadata
        )
    ]
    
    embeddings = [[0.1] * 768, [0.2] * 768]
    
    # Mock collection.add
    vector_store.collection.add = MagicMock()
    
    # Add documents
    vector_store.add_documents(chunks, embeddings, "doc-123")
    
    # Verify add was called
    vector_store.collection.add.assert_called_once()
    call_args = vector_store.collection.add.call_args[1]
    
    assert len(call_args["ids"]) == 2
    assert len(call_args["embeddings"]) == 2
    assert len(call_args["documents"]) == 2
    assert len(call_args["metadatas"]) == 2


def test_add_documents_mismatched_lengths(vector_store):
    """Test that mismatched chunks and embeddings raises error."""
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        page_count=1,
        document_type="pdf"
    )
    
    chunks = [
        DocumentChunk(
            content="Test content",
            chunk_index=0,
            metadata=metadata
        )
    ]
    
    embeddings = [[0.1] * 768, [0.2] * 768]  # More embeddings than chunks
    
    with pytest.raises(VectorStoreError) as exc_info:
        vector_store.add_documents(chunks, embeddings, "doc-123")
    
    assert "same length" in str(exc_info.value).lower()


def test_add_documents_empty_list(vector_store):
    """Test adding empty list of documents."""
    # Should not raise error, just log warning
    vector_store.add_documents([], [], "doc-123")


def test_similarity_search_success(vector_store):
    """Test similarity search."""
    query_embedding = [0.1] * 768
    
    # Mock query results
    vector_store.collection.query = MagicMock(return_value={
        "ids": [["doc1_0", "doc2_0"]],
        "documents": [["Content 1", "Content 2"]],
        "metadatas": [[{"document_id": "doc1"}, {"document_id": "doc2"}]],
        "distances": [[0.1, 0.2]]
    })
    
    results = vector_store.similarity_search(query_embedding, top_k=2)
    
    assert len(results) == 2
    assert results[0]["id"] == "doc1_0"
    assert results[0]["content"] == "Content 1"
    assert results[0]["distance"] == 0.1


def test_similarity_search_no_results(vector_store):
    """Test similarity search with no results."""
    query_embedding = [0.1] * 768
    
    # Mock empty results
    vector_store.collection.query = MagicMock(return_value={
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]]
    })
    
    results = vector_store.similarity_search(query_embedding)
    
    assert len(results) == 0


def test_similarity_search_with_filter(vector_store):
    """Test similarity search with metadata filter."""
    query_embedding = [0.1] * 768
    filter_metadata = {"document_type": "pdf"}
    
    vector_store.collection.query = MagicMock(return_value={
        "ids": [["doc1_0"]],
        "documents": [["Content 1"]],
        "metadatas": [[{"document_id": "doc1"}]],
        "distances": [[0.1]]
    })
    
    results = vector_store.similarity_search(
        query_embedding,
        filter_metadata=filter_metadata
    )
    
    # Verify filter was passed
    call_args = vector_store.collection.query.call_args[1]
    assert call_args["where"] == filter_metadata


def test_delete_document_success(vector_store):
    """Test deleting a document."""
    # Mock get results
    vector_store.collection.get = MagicMock(return_value={
        "ids": ["doc1_0", "doc1_1", "doc1_2"]
    })
    
    vector_store.collection.delete = MagicMock()
    
    deleted_count = vector_store.delete_document("doc1")
    
    assert deleted_count == 3
    vector_store.collection.delete.assert_called_once()


def test_delete_document_not_found(vector_store):
    """Test deleting non-existent document."""
    # Mock empty get results
    vector_store.collection.get = MagicMock(return_value={
        "ids": []
    })
    
    deleted_count = vector_store.delete_document("nonexistent")
    
    assert deleted_count == 0


def test_get_document_count(vector_store):
    """Test getting document count."""
    vector_store.collection.count = MagicMock(return_value=42)
    
    count = vector_store.get_document_count()
    
    assert count == 42


def test_get_document_count_error(vector_store):
    """Test getting document count when error occurs."""
    vector_store.collection.count = MagicMock(side_effect=Exception("Error"))
    
    count = vector_store.get_document_count()
    
    assert count == 0  # Should return 0 on error


def test_clear_collection(vector_store):
    """Test clearing collection."""
    vector_store.client.delete_collection = MagicMock()
    vector_store.client.get_or_create_collection = MagicMock(
        return_value=MagicMock()
    )
    
    vector_store.clear_collection()
    
    vector_store.client.delete_collection.assert_called_once()
    vector_store.client.get_or_create_collection.assert_called()


def test_get_stats(vector_store):
    """Test getting store statistics."""
    vector_store.collection.count = MagicMock(return_value=10)
    vector_store.collection.get = MagicMock(return_value={
        "metadatas": [
            {"document_id": "doc1"},
            {"document_id": "doc2"},
            {"document_id": "doc1"},
        ]
    })
    
    stats = vector_store.get_stats()
    
    assert stats["total_chunks"] == 10
    assert stats["unique_documents"] == 2
    assert "collection_name" in stats


def test_get_stats_error(vector_store):
    """Test getting stats when error occurs."""
    vector_store.collection.count = MagicMock(side_effect=Exception("Error"))
    
    stats = vector_store.get_stats()
    
    assert "error" in stats


def test_factory_function():
    """Test the factory function."""
    with patch('chromadb.PersistentClient'):
        with patch('backend.app.services.vector_store.Path.mkdir'):
            store = get_vector_store()
            assert isinstance(store, VectorStore)
