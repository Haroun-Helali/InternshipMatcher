"""Test configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF for testing."""
    return "tests/fixtures/sample_internship.pdf"


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from backend.app.core.config import Settings
    
    return Settings(
        environment="testing",
        chroma_persist_directory="./test_chroma_data",
        upload_dir="./test_uploads",
        temp_dir="./test_temp_files",
    )
