"""Logging configuration following best practices."""
import logging
import sys
from pathlib import Path

from backend.app.core.config import get_settings


def setup_logging() -> None:
    """Configure application logging.
    
    Sets up structured logging with appropriate levels and formats.
    """
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(log_dir / "app.log"),
        ],
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Name of the logger (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
