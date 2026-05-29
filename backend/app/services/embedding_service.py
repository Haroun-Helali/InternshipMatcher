"""Embedding service using Ollama for vector generation."""
import asyncio
from typing import List

import httpx

from backend.app.core.config import get_settings
from backend.app.core.exceptions import EmbeddingError
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Ollama.

    Implements Single Responsibility Principle - only handles embeddings.
    """

    def __init__(self):
        """Initialize embedding service with configuration."""
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.ollama_embedding_model
        self.timeout = self.settings.ollama_timeout

    async def health_check(self) -> bool:
        """Check if Ollama service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError(
                message="Cannot generate embedding for empty text",
                details={"text_length": len(text)}
            )

        try:
            import time as _time
            started = _time.perf_counter()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )

                if response.status_code != 200:
                    raise EmbeddingError(
                        message=f"Ollama API returned status {response.status_code}",
                        details={
                            "status_code": response.status_code,
                            "response": response.text
                        }
                    )

                data = response.json()
                embedding = data.get("embedding")

                if not embedding:
                    raise EmbeddingError(
                        message="No embedding in response",
                        details={"response": data}
                    )

                logger.info(
                    "ollama embeddings completed",
                    extra={
                        "ollama_call": "embeddings",
                        "ollama_model": self.model,
                        "latency_ms": round((_time.perf_counter() - started) * 1000, 1),
                        "dim": len(embedding),
                    },
                )
                return embedding

        except httpx.TimeoutException as e:
            raise EmbeddingError(
                message=f"Embedding generation timed out after {self.timeout}s",
                details={"timeout": self.timeout}
            ) from e
        except httpx.RequestError as e:
            raise EmbeddingError(
                message=f"Failed to connect to Ollama: {e}",
                details={"error": str(e), "url": self.base_url}
            ) from e
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
            raise EmbeddingError(
                message=f"Unexpected error: {e}",
                details={"error": str(e)}
            ) from e

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process concurrently

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If any embedding generation fails
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

        embeddings = []

        # Process in batches to avoid overwhelming the service
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Generate embeddings concurrently within batch
            tasks = [self.generate_embedding(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            embeddings.extend(batch_embeddings)

            logger.debug(f"Processed batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings


def get_embedding_service() -> EmbeddingService:
    """Get EmbeddingService instance.

    Factory function following Dependency Inversion Principle.
    """
    return EmbeddingService()
