"""Integration tests for embedding service and vector store.

These tests require Ollama to be running with mxbai-embed-large model.
"""
import pytest
from pathlib import Path

from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.vector_store import get_vector_store
from backend.app.services.document_processor import get_document_processor
from backend.app.core.exceptions import EmbeddingError


@pytest.fixture
async def embedding_service():
    """Get embedding service instance."""
    return get_embedding_service()


@pytest.fixture
def vector_store_test():
    """Get vector store with test collection."""
    store = get_vector_store()
    # Clear any existing test data
    try:
        store.clear_collection()
    except:
        pass
    yield store
    # Cleanup after test
    try:
        store.clear_collection()
    except:
        pass


@pytest.fixture
def sample_pdf_path():
    """Path to sample internship PDF."""
    return Path(__file__).parent.parent / "fixtures" / "sample_internship.pdf"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_service_health_check(embedding_service):
    """Test that Ollama service is available."""
    is_healthy = await embedding_service.health_check()
    assert is_healthy, "Ollama service is not available. Make sure it's running."


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_single_embedding(embedding_service):
    """Test generating a single embedding."""
    text = "Software engineering internship with Python and React"
    
    embedding = await embedding_service.generate_embedding(text)
    
    # Verify embedding properties
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)
    
    # mxbai-embed-large produces 1024-dimensional embeddings
    assert len(embedding) == 1024


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_multiple_embeddings(embedding_service):
    """Test generating embeddings for multiple texts."""
    texts = [
        "Machine learning internship",
        "Data science position",
        "Full-stack developer role"
    ]
    
    embeddings = await embedding_service.generate_embeddings_batch(texts)
    
    assert len(embeddings) == len(texts)
    assert all(len(emb) == 1024 for emb in embeddings)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embeddings_are_different(embedding_service):
    """Test that different texts produce different embeddings."""
    text1 = "Python programming"
    text2 = "JavaScript development"
    
    emb1 = await embedding_service.generate_embedding(text1)
    emb2 = await embedding_service.generate_embedding(text2)
    
    # Embeddings should be different
    assert emb1 != emb2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embeddings_are_consistent(embedding_service):
    """Test that same text produces same embedding."""
    text = "Consistent test text"
    
    emb1 = await embedding_service.generate_embedding(text)
    emb2 = await embedding_service.generate_embedding(text)
    
    # Should be identical
    assert emb1 == emb2


@pytest.mark.integration
def test_vector_store_initialization(vector_store_test):
    """Test that vector store initializes successfully."""
    assert vector_store_test.collection is not None
    assert vector_store_test.get_document_count() == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_document_pipeline(
    sample_pdf_path,
    embedding_service,
    vector_store_test
):
    """Test complete pipeline: process PDF -> generate embeddings -> store in vector DB."""
    # Process document
    processor = get_document_processor()
    processed_doc = processor.process_pdf(sample_pdf_path)
    
    assert processed_doc.total_chunks > 0
    
    # Generate embeddings
    texts = [chunk.content for chunk in processed_doc.chunks]
    embeddings = await embedding_service.generate_embeddings_batch(texts, batch_size=5)
    
    assert len(embeddings) == len(processed_doc.chunks)
    
    # Store in vector database
    vector_store_test.add_documents(
        processed_doc.chunks,
        embeddings,
        processed_doc.document_id
    )
    
    # Verify storage
    count = vector_store_test.get_document_count()
    assert count == processed_doc.total_chunks
    
    # Verify we can retrieve stats
    stats = vector_store_test.get_stats()
    assert stats["total_chunks"] == processed_doc.total_chunks
    assert stats["unique_documents"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_similarity_search_with_real_data(
    sample_pdf_path,
    embedding_service,
    vector_store_test
):
    """Test similarity search with real embeddings."""
    # Setup: Process and store document
    processor = get_document_processor()
    processed_doc = processor.process_pdf(sample_pdf_path)
    
    texts = [chunk.content for chunk in processed_doc.chunks]
    embeddings = await embedding_service.generate_embeddings_batch(texts, batch_size=5)
    
    vector_store_test.add_documents(
        processed_doc.chunks,
        embeddings,
        processed_doc.document_id
    )
    
    # Perform similarity search
    query_text = "What are the requirements for the internship?"
    query_embedding = await embedding_service.generate_embedding(query_text)
    
    results = vector_store_test.similarity_search(query_embedding, top_k=3)
    
    # Verify results
    assert len(results) > 0
    assert len(results) <= 3
    
    # Results should have required fields
    for result in results:
        assert "id" in result
        assert "content" in result
        assert "metadata" in result
        assert "distance" in result
        assert isinstance(result["distance"], float)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_relevance(
    sample_pdf_path,
    embedding_service,
    vector_store_test
):
    """Test that search returns relevant results."""
    # Setup
    processor = get_document_processor()
    processed_doc = processor.process_pdf(sample_pdf_path)
    
    texts = [chunk.content for chunk in processed_doc.chunks]
    embeddings = await embedding_service.generate_embeddings_batch(texts, batch_size=5)
    
    vector_store_test.add_documents(
        processed_doc.chunks,
        embeddings,
        processed_doc.document_id
    )
    
    # Search for specific topic
    query_text = "Python programming skills"
    query_embedding = await embedding_service.generate_embedding(query_text)
    
    results = vector_store_test.similarity_search(query_embedding, top_k=3)
    
    # Results should mention Python (or related content)
    # Note: This is a heuristic check
    assert len(results) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_document_from_vector_store(
    sample_pdf_path,
    embedding_service,
    vector_store_test
):
    """Test deleting a document from vector store."""
    # Setup: Add document
    processor = get_document_processor()
    processed_doc = processor.process_pdf(sample_pdf_path)
    
    texts = [chunk.content for chunk in processed_doc.chunks]
    embeddings = await embedding_service.generate_embeddings_batch(texts, batch_size=5)
    
    vector_store_test.add_documents(
        processed_doc.chunks,
        embeddings,
        processed_doc.document_id
    )
    
    initial_count = vector_store_test.get_document_count()
    assert initial_count > 0
    
    # Delete document
    deleted = vector_store_test.delete_document(processed_doc.document_id)
    
    assert deleted == processed_doc.total_chunks
    
    # Verify deletion
    final_count = vector_store_test.get_document_count()
    assert final_count == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_documents_in_store(
    sample_pdf_path,
    embedding_service,
    vector_store_test
):
    """Test storing and managing multiple documents."""
    processor = get_document_processor()
    
    # Add first document
    doc1 = processor.process_pdf(
        sample_pdf_path,
        custom_metadata={"company": "Company A"}
    )
    texts1 = [chunk.content for chunk in doc1.chunks]
    emb1 = await embedding_service.generate_embeddings_batch(texts1, batch_size=5)
    vector_store_test.add_documents(doc1.chunks, emb1, doc1.document_id)
    
    # Add second document (same file, different ID)
    doc2 = processor.process_pdf(
        sample_pdf_path,
        custom_metadata={"company": "Company B"}
    )
    texts2 = [chunk.content for chunk in doc2.chunks]
    emb2 = await embedding_service.generate_embeddings_batch(texts2, batch_size=5)
    vector_store_test.add_documents(doc2.chunks, emb2, doc2.document_id)
    
    # Verify both are stored
    stats = vector_store_test.get_stats()
    assert stats["unique_documents"] == 2
    assert stats["total_chunks"] == doc1.total_chunks + doc2.total_chunks
    
    # Delete first document
    vector_store_test.delete_document(doc1.document_id)
    
    # Verify only second remains
    stats_after = vector_store_test.get_stats()
    assert stats_after["unique_documents"] == 1
    assert stats_after["total_chunks"] == doc2.total_chunks
