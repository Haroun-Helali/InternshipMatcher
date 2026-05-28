"""
Query API endpoints for RAG functionality.
"""

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.app.core.exceptions import RAGPipelineError
from backend.app.models.api import (
    ConversationHistoryResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from backend.app.services.match_parser import extract_matches
from backend.app.services.rag_pipeline import create_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])

# Initialize RAG pipeline
rag_pipeline = create_rag_pipeline()


@router.post("/", response_model=QueryResponse)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """
    Query the knowledge base using RAG.

    Args:
        request: Query request with question and optional parameters

    Returns:
        Generated answer with source citations

    Raises:
        HTTPException: If query processing fails
    """
    try:
        logger.info(f"Processing query: {request.question[:100]}...")

        # Execute RAG query
        response = await rag_pipeline.query(
            question=request.question,
            top_k=request.top_k,
            session_id=request.session_id,
            filters=request.filters
        )

        # Format sources
        sources = [
            SourceReference(
                source_file=source["source_file"],
                page_number=source["page_number"],
                document_id=source["document_id"],
                content_preview=source["content_preview"]
            )
            for source in response.sources
        ]

        cleaned_answer, matches = extract_matches(response.answer)

        return QueryResponse(
            answer=cleaned_answer,
            sources=sources,
            matches=matches,
            query=response.query,
            model=response.model,
            session_id=request.session_id
        )

    except RAGPipelineError as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        ) from e


@router.websocket("/stream")
async def query_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming RAG responses.

    Client sends JSON: {"question": "...", "top_k": 5, "session_id": "..."}
    Server streams tokens as they're generated.
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive query from client
            data = await websocket.receive_json()

            question = data.get("question")
            if not question:
                await websocket.send_json({
                    "error": "Missing required field: question"
                })
                continue

            top_k = data.get("top_k", 5)
            session_id = data.get("session_id")
            filters = data.get("filters")

            logger.info(f"Streaming query: {question[:100]}...")

            try:
                # Send start signal
                await websocket.send_json({
                    "type": "start",
                    "session_id": session_id
                })

                # Collect sources while streaming
                sources = []
                full_answer = ""

                # Stream response tokens
                async for token in rag_pipeline.query_stream(
                    question=question,
                    top_k=top_k,
                    session_id=session_id,
                    filters=filters
                ):
                    full_answer += token
                    await websocket.send_json({
                        "type": "chunk",  # Changed from "token" to "chunk"
                        "content": token
                    })

                # Get sources from the last query
                try:
                    # Retrieve sources from RAG pipeline (already fetched during streaming)
                    results = rag_pipeline.last_retrieved_sources

                    sources = [
                        {
                            "document_id": result["metadata"].get("document_id", "unknown"),
                            "filename": result["metadata"].get("filename", "unknown"),
                            "chunk_index": result["metadata"].get("chunk_index", 0),
                            "content": result["content"],
                            "similarity_score": 1.0 - result.get("distance", 0.0)  # Convert distance to similarity
                        }
                        for result in results
                    ]
                except Exception as e:
                    logger.error(f"Failed to retrieve sources: {e}")
                    sources = []

                # Send sources
                await websocket.send_json({
                    "type": "sources",
                    "sources": sources
                })

                # Parse the structured matches block out of the full answer
                # and ship it so the frontend doesn't need to re-parse the
                # streamed text. `cleaned_answer` is the visible message with
                # the JSON code-fence removed.
                cleaned_answer, matches = extract_matches(full_answer)
                await websocket.send_json({
                    "type": "matches",
                    "cleaned_answer": cleaned_answer,
                    "matches": [m.model_dump() for m in matches],
                })

                # Send completion signal
                await websocket.send_json({
                    "type": "done"
                })

            except RAGPipelineError as e:
                logger.error(f"RAG pipeline error: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)  # Changed from "error" to "message"
                })
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": "An unexpected error occurred"  # Changed from "error" to "message"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    # Do not close the shared RAG pipeline here; it's a module-level singleton
    # and should live for the app lifetime. Closing it causes subsequent
    # requests to fail with "client has been closed" errors.


@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str) -> ConversationHistoryResponse:
    """
    Get conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        Conversation history
    """
    try:
        history = rag_pipeline.get_conversation_history(session_id)

        return ConversationHistoryResponse(
            session_id=session_id,
            turns=history,
            turn_count=len(history)
        )

    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        ) from e


@router.delete("/history/{session_id}")
async def clear_conversation_history(session_id: str) -> dict:
    """
    Clear conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        rag_pipeline.clear_conversation(session_id)

        return {
            "success": True,
            "message": f"Conversation history cleared for session {session_id}"
        }

    except Exception as e:
        logger.error(f"Failed to clear history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to clear conversation history"
        ) from e
