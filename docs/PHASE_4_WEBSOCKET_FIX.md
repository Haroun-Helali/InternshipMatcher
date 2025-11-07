# Phase 4 Fix: WebSocket Communication Bug

## Issue
Users could send messages to the chatbot but weren't receiving responses. The chat interface would show the loading state but no response would appear.

## Root Cause Analysis

### Problem 1: Message Type Mismatch
**Backend was sending:**
```json
{
  "type": "token",
  "content": "text chunk"
}
```

**Frontend was expecting:**
```json
{
  "type": "chunk",
  "content": "text chunk"
}
```

### Problem 2: Missing Sources
The backend WebSocket endpoint (`/query/stream`) was sending a `"done"` message without including the source citations that the frontend expected.

### Problem 3: Error Message Field Mismatch
**Backend was sending:**
```json
{
  "type": "error",
  "error": "error message"
}
```

**Frontend was expecting:**
```json
{
  "type": "error",
  "message": "error message"
}
```

## Solution

### Changes Made to `backend/app/api/query.py`

1. **Fixed Message Type** (Line ~125)
   - Changed `"type": "token"` to `"type": "chunk"`
   - This allows the frontend to properly identify and process streaming chunks

2. **Added Source Retrieval** (Lines ~127-150)
   - After streaming completes, query the vector store for sources
   - Build source references with document metadata
   - Send sources in the expected format before the "done" message

3. **Fixed Error Message Format** (Lines ~165-175)
   - Changed `"error": str(e)` to `"message": str(e)`
   - Ensures frontend can properly display error messages

4. **Added Import**
   - Added `from backend.app.services.vector_store import VectorStore`
   - Required for source retrieval functionality

### Code Changes

```python
# Before (BROKEN)
async for token in rag_pipeline.query_stream(...):
    await websocket.send_json({
        "type": "token",  # ❌ Wrong type
        "content": token
    })

await websocket.send_json({
    "type": "done"  # ❌ No sources
})
```

```python
# After (FIXED)
# Collect answer while streaming
full_answer = ""
sources = []

async for token in rag_pipeline.query_stream(...):
    full_answer += token
    await websocket.send_json({
        "type": "chunk",  # ✅ Correct type
        "content": token
    })

# Retrieve sources from vector store
vector_store = VectorStore()
results = vector_store.similarity_search(
    query=question,
    k=top_k,
    filters=filters
)

sources = [
    {
        "document_id": doc.metadata.get("document_id", "unknown"),
        "filename": doc.metadata.get("filename", "unknown"),
        "chunk_index": doc.metadata.get("chunk_index", 0),
        "content": doc.page_content,
        "similarity_score": doc.metadata.get("similarity_score", 0.0)
    }
    for doc in results
]

# Send sources before completion
await websocket.send_json({
    "type": "sources",  # ✅ Send sources
    "sources": sources
})

await websocket.send_json({
    "type": "done"
})
```

## WebSocket Message Flow (Fixed)

### Complete Message Sequence

1. **Client → Server: Initial Request**
```json
{
  "question": "What internship opportunities are available?",
  "session_id": "session_12345",
  "include_sources": true,
  "top_k": 5
}
```

2. **Server → Client: Start Signal**
```json
{
  "type": "start",
  "session_id": "session_12345"
}
```

3. **Server → Client: Streaming Chunks** (multiple messages)
```json
{"type": "chunk", "content": "Based "}
{"type": "chunk", "content": "on the "}
{"type": "chunk", "content": "uploaded "}
{"type": "chunk", "content": "documents... "}
```

4. **Server → Client: Sources**
```json
{
  "type": "sources",
  "sources": [
    {
      "document_id": "doc_123",
      "filename": "internship_listing.pdf",
      "chunk_index": 5,
      "content": "We are seeking software engineering interns...",
      "similarity_score": 0.89
    }
  ]
}
```

5. **Server → Client: Completion**
```json
{
  "type": "done"
}
```

## Frontend Compatibility

The frontend (`frontend/lib/api.ts` and `frontend/components/CenterChat.tsx`) already had the correct implementation expecting:
- `type: "chunk"` for streaming tokens
- `type: "sources"` with `sources` array
- `type: "error"` with `message` field

No frontend changes were required - only backend fixes.

## Testing

### Manual Test Steps
1. Start backend: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000
4. Upload a PDF document
5. Ask a question: "What are the internship requirements?"
6. Verify:
   - ✅ Response appears token-by-token (streaming)
   - ✅ Citations show at the end
   - ✅ Hover over citations shows source excerpts
   - ✅ No console errors

### Expected Behavior
- Messages stream in real-time (visible typing effect)
- Source citations appear after response completes
- Citations show document names
- Hovering citations displays content excerpts

## Verification

### Check Backend Logs
```
INFO: WebSocket connection established
INFO: Streaming query: What are the internship requirements...
INFO: Query completed successfully
```

### Check Browser Console
```
WebSocket connected
Received: {type: "start", session_id: "..."}
Received: {type: "chunk", content: "Based "}
Received: {type: "chunk", content: "on..."}
Received: {type: "sources", sources: [...]}
Received: {type: "done"}
WebSocket connection closed
```

## Impact
- ✅ Chat functionality now works end-to-end
- ✅ Users receive streaming responses in real-time
- ✅ Source citations properly displayed
- ✅ Error handling improved
- ✅ No breaking changes to other functionality

## Related Files
- `backend/app/api/query.py` - WebSocket endpoint (MODIFIED)
- `frontend/lib/api.ts` - API client (NO CHANGES)
- `frontend/components/CenterChat.tsx` - Chat UI (NO CHANGES)

## Follow-up Actions
- ✅ Backend server restarted automatically (uvicorn --reload)
- ✅ Frontend running on http://localhost:3000
- ⏳ Commit changes to git
- ⏳ Update progress documentation
