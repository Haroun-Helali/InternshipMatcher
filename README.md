# Internship Matcher

AI-powered internship matching: upload internship PDFs, ask questions in natural language, get answers with cited sources and a ranked list of matching opportunities.

Built on FastAPI + LangChain + ChromaDB on the backend and Next.js 16 on the frontend, with local LLM inference via Ollama.

## What works today

End-to-end:

- **Upload** PDFs through the UI or `POST /api/v1/documents/upload`. The backend extracts text, splits into chunks, embeds via `mxbai-embed-large`, and stores in ChromaDB.
- **Query** via the chat UI or `POST /api/v1/query/`. Retrieval-augmented prompts run through `llama3.2` and return an answer plus cited source pages.
- **Stream** tokens through `ws://.../api/v1/query/stream` for real-time chat responses.
- **Matches sidebar**: the LLM emits a structured JSON summary that the frontend renders as a ranked list of internships with "View PDF" links to the original document served from `/files`.
- **Conversation history** is kept per `session_id`.

## Architecture

```
Next.js (port 3000)  ─HTTP/WS─►  FastAPI (port 8000)  ─►  RAG pipeline
                                                              │
                                                ┌─────────────┼──────────────┐
                                                ▼             ▼              ▼
                                            Ollama       ChromaDB         PDF
                                          (port 11434)   (./chroma_data)  parser
```

Models pulled on first run:
- `llama3.2:latest` — answer generation (~2 GB)
- `mxbai-embed-large:latest` — embeddings (~669 MB)

## Prerequisites

- Python 3.10 – 3.13 (`langchain-text-splitters==0.0.1` and `chromadb==0.4.22` are pinned and don't build on 3.14)
- Node.js 18+
- [Ollama](https://ollama.ai/download)
- ~3 GB free disk for the model weights

## Quick start

### macOS / Linux

```bash
./start.sh install   # one-time: venv + pip + npm install + pull models
./start.sh all       # start backend + frontend
```

Logs land in `logs/backend.log` and `logs/frontend.log`. The PIDs are written to `.backend.pid` and `.frontend.pid` for easy `kill $(cat .backend.pid)`.

### Windows

```powershell
./start.ps1 install
./start.ps1 all
```

### Manual

```bash
# Backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p uploads temp_files logs chroma_data
ollama serve &                          # start daemon
ollama pull llama3.2:latest
ollama pull mxbai-embed-large:latest
python -m backend.app.main              # serves on :8000

# Frontend (separate shell)
cd frontend && npm install && npm run dev   # serves on :3000
```

Once up:

- Frontend: <http://localhost:3000>
- API docs: <http://localhost:8000/api/v1/docs>
- Health: <http://localhost:8000/health>

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/health` | Liveness probe |
| `POST`   | `/api/v1/documents/upload` | Upload PDF, processed in background |
| `GET`    | `/api/v1/documents/` | List indexed documents |
| `GET`    | `/api/v1/documents/stats` | Counts and total size |
| `GET`    | `/api/v1/documents/{document_id}/status` | Lifecycle state: pending / processing / ready / failed |
| `DELETE` | `/api/v1/documents/{document_id}` | Remove a document |
| `POST`   | `/api/v1/query/` | Ask a question, get answer + sources |
| `WS`     | `/api/v1/query/stream` | Streaming token responses |
| `GET`    | `/api/v1/query/history/{session_id}` | Conversation transcript |
| `DELETE` | `/api/v1/query/history/{session_id}` | Reset a conversation |
| `GET`    | `/files/{filename}` | Static PDF download |

Full OpenAPI schema at `/api/v1/openapi.json`.

## Configuration

All settings live in `.env` (copy from `.env.example`). Notable knobs:

| Var | Default | Notes |
|---|---|---|
| `BACKEND_HOST` / `BACKEND_PORT` | `0.0.0.0` / `8000` | |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | |
| `OLLAMA_LLM_MODEL` | `llama3.2:latest` | |
| `OLLAMA_EMBEDDING_MODEL` | `mxbai-embed-large:latest` | |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `50` | Text-splitter knobs |
| `RAG_TOP_K_RESULTS` | `5` | Retrieval depth |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated |

## Tests

```bash
source venv/bin/activate
pytest -m "not integration"          # unit + e2e mocks, no Ollama needed
pytest -m integration                # requires Ollama + both models
pytest                                # everything
```

Coverage report at `htmlcov/index.html` after a run.

## Project layout

```
backend/app/
  api/          # FastAPI routers (documents, query)
  core/         # config, logging, exceptions
  services/     # document_processor, embedding_service, vector_store, rag_pipeline, prompts
  models/       # Pydantic schemas
  cli/          # dev CLI utilities
  utils/
frontend/
  app/          # Next.js App Router pages
  components/   # CenterChat, LeftSidebar, RightSidebar, etc.
  lib/          # api client, WebSocket helpers
  contexts/     # React contexts (AppContext)
tests/
  unit/ integration/ fixtures/
  conftest.py
```

## Known limitations

- **No authentication**: anyone reaching the API can upload, query, or delete. Add an API-key gate before exposing the service.
- **In-process services**: the FastAPI app holds singletons for the RAG pipeline, embedding service, and vector store. Concurrent WebSocket clients share these, which can cause head-of-line stalls. Per-request pooling is in Phase C.
- **Pydantic v2 class-config warnings**: a few models in `backend/app/models/document.py` still use the old `class Config:` form. Cosmetic — fix by migrating to `model_config = ConfigDict(...)` whenever they're next touched.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## License

MIT
