"""
RAG (Retrieval-Augmented Generation) Pipeline Service.

This module orchestrates the complete RAG workflow:
1. Convert user query to embedding
2. Retrieve relevant context from vector store
3. Build prompt with context
4. Generate response using LLM
5. Extract citations and format output
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from backend.app.core.config import get_settings
from backend.app.core.exceptions import RAGPipelineError
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.prompts import PromptTemplates
from backend.app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from RAG pipeline."""

    answer: str
    sources: List[Dict[str, Any]]
    context_used: str
    query: str
    model: str


@dataclass
class ConversationTurn:
    """Single turn in conversation history."""

    question: str
    answer: str


class RAGPipeline:
    """
    Main RAG pipeline orchestrator.

    Implements the complete Retrieval-Augmented Generation workflow using
    vector search and LLM generation.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        prompt_templates: Optional[PromptTemplates] = None,
    ):
        """
        Initialize RAG pipeline.

        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector store for document retrieval
            prompt_templates: Prompt templates (uses default if None)
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.prompt_templates = prompt_templates or PromptTemplates()
        self.settings = get_settings()

        # HTTP client for Ollama API
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),  # 2 minutes for generation
            base_url=self.settings.ollama_base_url,
        )

        # Conversation history (session_id -> turns)
        self.conversations: Dict[str, List[ConversationTurn]] = {}

        logger.info(
            "RAG Pipeline initialized",
            extra={
                "llm_model": self.settings.ollama_llm_model,
                "top_k": self.settings.rag_top_k_results,
            },
        )

    async def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RAGResponse:
        """
        Execute complete RAG query pipeline.

        Args:
            question: User's question
            top_k: Number of top results to retrieve (default from config)
            session_id: Session ID for conversation history
            filters: Metadata filters for vector search

        Returns:
            RAGResponse with answer and sources

        Raises:
            RAGPipelineError: If pipeline execution fails
        """
        try:
            logger.info(f"RAG query started: {question[:100]}...")

            # Step 1: Generate query embedding
            logger.debug("Generating query embedding")
            query_embedding = await self.embedding_service.generate_embedding(question)

            # Step 2: Retrieve relevant context
            top_k = top_k or self.settings.rag_top_k_results
            logger.debug(f"Retrieving top {top_k} results from vector store")

            results = self.vector_store.similarity_search(
                query_embedding=query_embedding, top_k=top_k, filter_metadata=filters
            )

            # Step 3: Build context and prompt
            if not results:
                logger.warning("No relevant context found for query")
                answer = self.prompt_templates.build_no_context_prompt(question)
                return RAGResponse(
                    answer=answer,
                    sources=[],
                    context_used="",
                    query=question,
                    model=self.settings.ollama_llm_model,
                )

            # Extract chunks and format context
            chunks = [
                {
                    "content": result["content"],
                    "metadata": {
                        "source_file": result["metadata"].get("filename", "Unknown"),
                        "page_number": result["metadata"].get("chunk_index", 0),
                        "document_id": result["metadata"]["document_id"],
                    },
                }
                for result in results
            ]

            context = self.prompt_templates.format_context_from_chunks(chunks)

            # Build prompt with conversation history if available
            if session_id and session_id in self.conversations:
                history = [
                    {"question": turn.question, "answer": turn.answer}
                    for turn in self.conversations[session_id]
                ]
                prompt = self.prompt_templates.build_followup_prompt(
                    question=question, context=context, conversation_history=history
                )
            else:
                prompt = self.prompt_templates.build_query_prompt(
                    question=question, context=context
                )

            # Step 4: Generate LLM response
            logger.debug("Generating LLM response")
            answer = await self._generate_response(prompt)

            # Step 5: Store conversation turn
            if session_id:
                if session_id not in self.conversations:
                    self.conversations[session_id] = []
                self.conversations[session_id].append(
                    ConversationTurn(question=question, answer=answer)
                )

            # Extract source information
            sources = [
                {
                    "source_file": chunk["metadata"]["source_file"],
                    "page_number": chunk["metadata"]["page_number"],
                    "document_id": chunk["metadata"]["document_id"],
                    "content_preview": chunk["content"][:200] + "...",
                }
                for chunk in chunks
            ]

            logger.info("RAG query completed successfully")

            return RAGResponse(
                answer=answer,
                sources=sources,
                context_used=context,
                query=question,
                model=self.settings.ollama_llm_model,
            )

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}", exc_info=True)
            raise RAGPipelineError(
                f"Failed to execute RAG query: {str(e)}", details={"question": question}
            ) from e

    async def query_stream(
        self,
        question: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute the RAG query and stream discriminated events.

        Events:
            - {"type": "sources", "sources": [...]} — emitted exactly once
              before any tokens, even if the list is empty.
            - {"type": "token", "content": str} — generated text tokens.

        Returning events instead of bare strings lets the caller carry the
        sources alongside the stream without the pipeline holding per-request
        state on a shared singleton (which raced under concurrent WS clients).
        """
        try:
            logger.info(f"RAG streaming query started: {question[:100]}...")

            query_embedding = await self.embedding_service.generate_embedding(question)
            top_k = top_k or self.settings.rag_top_k_results

            results = self.vector_store.similarity_search(
                query_embedding=query_embedding, top_k=top_k, filter_metadata=filters
            )

            sources_payload = [
                {
                    "document_id": r["metadata"].get("document_id", "unknown"),
                    "filename": r["metadata"].get("filename", "unknown"),
                    "chunk_index": r["metadata"].get("chunk_index", 0),
                    "content": r["content"],
                    "similarity_score": 1.0 - r.get("distance", 0.0),
                }
                for r in results
            ]
            yield {"type": "sources", "sources": sources_payload}

            if not results:
                yield {
                    "type": "token",
                    "content": self.prompt_templates.build_no_context_prompt(question),
                }
                return

            chunks = [
                {
                    "content": result["content"],
                    "metadata": {
                        "source_file": result["metadata"].get("filename", "Unknown"),
                        "page_number": result["metadata"].get("chunk_index", 0),
                        "document_id": result["metadata"]["document_id"],
                    },
                }
                for result in results
            ]

            context = self.prompt_templates.format_context_from_chunks(chunks)

            if session_id and session_id in self.conversations:
                history = [
                    {"question": turn.question, "answer": turn.answer}
                    for turn in self.conversations[session_id]
                ]
                prompt = self.prompt_templates.build_followup_prompt(
                    question=question, context=context, conversation_history=history
                )
            else:
                prompt = self.prompt_templates.build_query_prompt(
                    question=question, context=context
                )

            full_answer = ""
            async for token in self._generate_response_stream(prompt):
                full_answer += token
                yield {"type": "token", "content": token}

            if session_id:
                if session_id not in self.conversations:
                    self.conversations[session_id] = []
                self.conversations[session_id].append(
                    ConversationTurn(question=question, answer=full_answer)
                )

        except Exception as e:
            logger.error(f"RAG streaming pipeline error: {e}", exc_info=True)
            raise RAGPipelineError(
                f"Failed to execute streaming RAG query: {str(e)}",
                details={"question": question},
            ) from e

    async def _generate_response(self, prompt: str) -> str:
        """
        Generate response from Ollama LLM.

        Args:
            prompt: Complete prompt with context

        Returns:
            Generated response text

        Raises:
            RAGPipelineError: If generation fails
        """
        try:
            payload = {
                "model": self.settings.ollama_llm_model,
                "prompt": f"{self.prompt_templates.SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }

            started = time.perf_counter()
            response = await self.http_client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "ollama generate completed",
                extra={
                    "ollama_call": "generate",
                    "ollama_model": self.settings.ollama_llm_model,
                    "latency_ms": round(elapsed_ms, 1),
                    "eval_count": data.get("eval_count"),
                },
            )
            answer = data.get("response", "")

            if not answer:
                raise RAGPipelineError("Empty response from LLM")

            return answer

        except httpx.HTTPError as e:
            raise RAGPipelineError(
                f"HTTP error during LLM generation: {str(e)}",
                details={"status_code": getattr(e.response, "status_code", None)},
            ) from e
        except Exception as e:
            raise RAGPipelineError(
                f"Failed to generate LLM response: {str(e)}"
            ) from e

    async def _generate_response_stream(self, prompt: str) -> AsyncIterator[str]:
        """
        Generate streaming response from Ollama LLM.

        Args:
            prompt: Complete prompt with context

        Yields:
            Response tokens

        Raises:
            RAGPipelineError: If generation fails
        """
        try:
            payload = {
                "model": self.settings.ollama_llm_model,
                "prompt": f"{self.prompt_templates.SYSTEM_PROMPT}\n\n{prompt}",
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }

            started = time.perf_counter()
            tokens_yielded = 0
            async with self.http_client.stream(
                "POST", "/api/generate", json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)
                        if "response" in data:
                            tokens_yielded += 1
                            yield data["response"]
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "ollama generate (stream) completed",
                extra={
                    "ollama_call": "generate_stream",
                    "ollama_model": self.settings.ollama_llm_model,
                    "latency_ms": round(elapsed_ms, 1),
                    "tokens": tokens_yielded,
                },
            )

        except httpx.HTTPError as e:
            raise RAGPipelineError(
                f"HTTP error during streaming generation: {str(e)}",
                details={"status_code": getattr(e.response, "status_code", None)},
            ) from e
        except Exception as e:
            raise RAGPipelineError(
                f"Failed to stream LLM response: {str(e)}"
            ) from e

    def clear_conversation(self, session_id: str) -> None:
        """
        Clear conversation history for a session.

        Args:
            session_id: Session ID to clear
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Cleared conversation history for session {session_id}")

    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session ID

        Returns:
            List of conversation turns
        """
        if session_id not in self.conversations:
            return []

        return [
            {"question": turn.question, "answer": turn.answer}
            for turn in self.conversations[session_id]
        ]

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        await self.http_client.aclose()
        logger.info("RAG Pipeline closed")


def create_rag_pipeline(
    embedding_service: Optional[EmbeddingService] = None,
    vector_store: Optional[VectorStore] = None,
) -> RAGPipeline:
    """
    Factory function to create RAG pipeline with dependencies.

    Args:
        embedding_service: Optional embedding service (creates default if None)
        vector_store: Optional vector store (creates default if None)

    Returns:
        Configured RAGPipeline instance
    """
    from backend.app.services.embedding_service import get_embedding_service
    from backend.app.services.vector_store import get_vector_store

    if embedding_service is None:
        embedding_service = get_embedding_service()

    if vector_store is None:
        vector_store = get_vector_store()

    return RAGPipeline(
        embedding_service=embedding_service, vector_store=vector_store
    )
