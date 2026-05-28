"""Tests for core configuration."""
from backend.app.core.config import Settings, get_settings


def test_settings_default_values():
    """Test that settings load with default values."""
    settings = Settings()

    assert settings.app_name == "Internship RAG Application"
    assert settings.chunk_size == 500
    assert settings.rag_top_k_results == 5
    assert settings.ollama_embedding_model == "mxbai-embed-large:latest"
    assert settings.ollama_llm_model == "llama3.2:latest"


def test_cors_origins_parsing():
    """Test CORS origins are properly parsed."""
    settings = Settings(cors_origins="http://localhost:3000,http://127.0.0.1:3000")

    origins = settings.cors_origins_list
    assert len(origins) == 2
    assert "http://localhost:3000" in origins


def test_allowed_extensions_parsing():
    """Test allowed extensions are properly parsed."""
    settings = Settings(allowed_extensions="pdf,docx")

    extensions = settings.allowed_extensions_list
    assert len(extensions) == 2
    assert "pdf" in extensions
    assert "docx" in extensions


def test_max_file_size_conversion():
    """Test file size conversion from MB to bytes."""
    settings = Settings(max_file_size_mb=10)

    assert settings.max_file_size_bytes == 10 * 1024 * 1024


def test_get_settings_returns_cached_instance():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
