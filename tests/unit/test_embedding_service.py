"""Unit tests for embedding service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.core.exceptions import EmbeddingError
from backend.app.services.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture
def embedding_service():
    """Create embedding service instance."""
    return EmbeddingService()


@pytest.mark.asyncio
async def test_service_initialization(embedding_service):
    """Test that service initializes with correct settings."""
    assert embedding_service.base_url == "http://localhost:11434"
    assert embedding_service.model == "mxbai-embed-large:latest"
    assert embedding_service.timeout == 120


@pytest.mark.asyncio
async def test_generate_embedding_success(embedding_service):
    """Test successful embedding generation."""
    mock_embedding = [0.1] * 768  # Typical embedding dimension

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": mock_embedding}

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await embedding_service.generate_embedding("test text")

        assert result == mock_embedding
        assert len(result) == 768


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service):
    """Test that empty text raises error."""
    with pytest.raises(EmbeddingError) as exc_info:
        await embedding_service.generate_embedding("")

    assert "empty text" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_generate_embedding_whitespace_only(embedding_service):
    """Test that whitespace-only text raises error."""
    with pytest.raises(EmbeddingError) as exc_info:
        await embedding_service.generate_embedding("   \n\t   ")

    assert "empty text" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_generate_embedding_api_error(embedding_service):
    """Test handling of API error responses."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(EmbeddingError) as exc_info:
            await embedding_service.generate_embedding("test text")

        assert "500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_embedding_timeout(embedding_service):
    """Test handling of timeout errors."""
    import httpx

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        with pytest.raises(EmbeddingError) as exc_info:
            await embedding_service.generate_embedding("test text")

        assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_generate_embedding_connection_error(embedding_service):
    """Test handling of connection errors."""
    import httpx

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )

        with pytest.raises(EmbeddingError) as exc_info:
            await embedding_service.generate_embedding("test text")

        assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_embedding_no_embedding_in_response(embedding_service):
    """Test handling of response without embedding."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"no_embedding": "here"}

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(EmbeddingError) as exc_info:
            await embedding_service.generate_embedding("test text")

        assert "No embedding" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_embeddings_batch_success(embedding_service):
    """Test batch embedding generation."""
    texts = ["text1", "text2", "text3"]
    mock_embedding = [0.1] * 768

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": mock_embedding}

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        results = await embedding_service.generate_embeddings_batch(texts)

        assert len(results) == 3
        assert all(len(emb) == 768 for emb in results)


@pytest.mark.asyncio
async def test_generate_embeddings_batch_empty_list(embedding_service):
    """Test batch generation with empty list."""
    results = await embedding_service.generate_embeddings_batch([])
    assert results == []


@pytest.mark.asyncio
async def test_generate_embeddings_batch_custom_batch_size(embedding_service):
    """Test batch generation with custom batch size."""
    texts = ["text1", "text2", "text3", "text4", "text5"]
    mock_embedding = [0.1] * 768

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": mock_embedding}

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        results = await embedding_service.generate_embeddings_batch(texts, batch_size=2)

        assert len(results) == 5


@pytest.mark.asyncio
async def test_health_check_success(embedding_service):
    """Test successful health check."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await embedding_service.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(embedding_service):
    """Test health check when service is down."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        result = await embedding_service.health_check()
        assert result is False


def test_factory_function():
    """Test the factory function."""
    service = get_embedding_service()
    assert isinstance(service, EmbeddingService)
