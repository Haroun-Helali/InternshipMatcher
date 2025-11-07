"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core import get_logger, get_settings, setup_logging

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events."""
    # Startup
    logger.info("Starting Internship RAG Application...")
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application.
    
    Following Dependency Injection and Single Responsibility principles.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment
        }
    
    # Register API routers
    from backend.app.api import documents, query
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(query.router, prefix=settings.api_v1_prefix)
    
    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True if settings.environment == "development" else False,
    )
