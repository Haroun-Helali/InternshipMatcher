"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core import get_logger, get_settings, setup_logging
from backend.app.core.auth import install_api_key_middleware
from backend.app.core.request_id import RequestIDMiddleware

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

    # Request-ID propagation runs first so auth/log emissions carry the id.
    app.add_middleware(RequestIDMiddleware)

    # API key auth — no-op when settings.api_key is empty.
    install_api_key_middleware(app, settings)
    if settings.api_key:
        logger.info("API key auth enabled")
    else:
        logger.warning("API key auth DISABLED (set API_KEY to enable)")

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

    # Serve uploaded files statically for reference
    try:
        app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")
        logger.info(f"Mounted static files at /files from {settings.upload_dir}")
    except Exception as e:
        logger.error(f"Failed to mount static files: {e}")

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
