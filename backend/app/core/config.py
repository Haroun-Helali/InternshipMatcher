"""Core configuration module following SOLID principles."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Implements Single Responsibility Principle - only manages configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "Internship RAG Application"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "mxbai-embed-large:latest"
    ollama_llm_model: str = "llama3.2:latest"
    ollama_timeout: int = 120

    # ChromaDB
    chroma_persist_directory: str = "./chroma_data"
    chroma_collection_name: str = "internship_documents"

    # Document metadata store (SQLite). Path is relative to the working
    # directory by default; override DOCUMENT_DB_PATH to point elsewhere.
    document_db_path: str = "./documents.sqlite"

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 50
    rag_top_k_results: int = 3  # Reduced from 5 to 3 for faster responses
    max_context_length: int = 2000

    # Documents
    max_file_size_mb: int = 10
    allowed_extensions: str = "pdf,docx"
    upload_dir: str = "./uploads"
    temp_dir: str = "./temp_files"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    rate_limit_per_minute: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions into a list."""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Using Dependency Inversion Principle - allows easy testing and mocking.
    """
    return Settings()
