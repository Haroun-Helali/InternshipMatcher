# Roadmap

A living plan for taking this from a working demo to a production-shaped product. Phases are ordered by leverage; each one builds on the last.

## Phase A — Foundations (1 day, in progress)

Low-risk hygiene that unblocks everything after it. No architecture decisions.

- [x] `.env` properly gitignored (only `.env.example` tracked)
- [x] `start.sh` for macOS/Linux mirroring `start.ps1`
- [x] README rewritten to match actual implementation state
- [x] `docs/ROADMAP.md` (this file)
- [ ] `tests/e2e/test_upload_query.py` happy-path: upload sample PDF → wait for embedding → query → assert answer + sources
- [ ] `.github/workflows/ci.yml` running `pytest -m "not integration"` and `ruff check` on every push

## Phase B — Correctness (3–5 days)

Kill the fragility points the audit surfaced.

- **Document ID consistency**. The upload endpoint at [documents.py:124](../backend/app/api/documents.py#L124) generates one `document_id`, returns it to the client, then `process_document_background` calls `doc_processor.process_pdf` which mints its *own* internal ID and stores under that. The two never reconcile. Fix: thread the upload ID through to the processor, or drop the upload-side ID. Surfaced by the new e2e test, which currently works around it by matching documents by filename.
- **Server-side match extraction**. Move the JSON parsing now done in [CenterChat.tsx:34-90](../frontend/components/CenterChat.tsx#L34-L90) into the backend. `QueryResponse` gains a typed `matches: List[Match]` field. The LLM still emits JSON, but parsing happens once, with a validator, and clients consume structured data.
- **Ruff cleanup**. 463 pre-existing lint warnings (mostly trailing whitespace, unused imports). Run `ruff check --fix backend tests`, review the result, flip `continue-on-error` off in `.github/workflows/ci.yml`.
- **Upload status endpoint**. `GET /api/v1/documents/{id}/status` returns `{state: "uploading"|"processing"|"ready"|"failed", chunks_indexed: N, error?: str}`. Frontend polls or subscribes; users stop guessing whether their PDF is ready.
- **SQLite metadata store**. Replace the in-memory `documents_metadata = {}` at [documents.py:35](../backend/app/api/documents.py#L35) with a `documents` table (SQLAlchemy or raw `sqlite3`). Vectors stay in ChromaDB. Survives reboots.
- **Dependency refresh**. Upgrade `langchain-text-splitters`, `chromadb`, `ollama`, `fastapi`, `pydantic` to current versions. Run unit + integration tests against the new pins; bump `requires-python` if needed.

Definition of done: a backend restart no longer wipes the document list; a malformed LLM response no longer empties the matches sidebar; CI passes on Python 3.12 with the upgraded deps.

## Phase C — Productization (1–2 weeks)

Make it deployable and pleasant to use.

- **API key auth**. `X-API-Key` header middleware. One key in `.env` for dev, rotation via env var swap. Block unauthenticated requests at every router except `/health`.
- **Docker**. `Dockerfile` (multi-stage: builder + runtime) for the backend, `Dockerfile` for the frontend, `docker-compose.yml` covering backend + frontend + ollama + a chroma volume. `docker-compose up` should be the new quick-start.
- **Per-connection RAG pipeline**. Refactor the module-singleton workaround at [query.py:184](../backend/app/api/query.py#L184) so concurrent WebSocket clients don't share state. Either instantiate per-request or use a connection pool.
- **Frontend polish**: real loading states during embedding, error toasts on failed uploads/queries, mobile breakpoint (sidebars collapse to drawer), WebSocket auto-reconnect.
- **Structured logging**. Switch to `structlog` or stdlib logging with JSON formatter. Add a request-ID middleware. Log Ollama call latency.

Definition of done: `docker-compose up` brings the whole stack live with one command; an unauthenticated request returns 401; the UI is usable on a phone.

## Phase D — Real product (ongoing)

Decisions that turn this into a product, not just an app.

- **User accounts + sessions**. JWT or session cookies. Per-user document scoping — uploads belong to a user, queries only retrieve from their corpus (or a shared pool).
- **Ingestion pipeline**. Where do internship PDFs come from at scale? Options:
  - Manual upload (current)
  - Bulk CSV/zip import
  - Web scraping from job boards
  - Partner feed (API integration with a careers platform)
  Pick one based on user research; build a separate `ingest/` service.
- **Quality loop**. Thumbs-up/-down on each match. Log feedback to a `match_feedback` table. Build a small eval harness: a set of "golden" question/expected-source pairs, run nightly, track precision@k over time.
- **Observability**. OpenTelemetry traces from request → retrieval → LLM. Latency dashboards. Alert on Ollama unavailability.
- **Retrieval quality**. Experiment with hybrid retrieval (BM25 + dense), reranking with a cross-encoder, prompt tuning. Driven by the eval harness above.
- **Multi-tenant deployment**. If we ever host for multiple orgs: per-tenant collections in ChromaDB, per-tenant API keys, billing/quota tracking.

Definition of done: a stakeholder can sign up, upload their own corpus, query it, and the team has data on whether the answers were good.

## Out of scope (for now)

- Mobile native apps — the responsive web UI is enough.
- Fine-tuning a custom model — `llama3.2` + good prompts cover the demo case.
- Self-hosted vector DB beyond ChromaDB — only revisit if scaling forces it.

## How to contribute to this roadmap

Each phase item should be a closeable PR. When an item ships, check it off here and link the PR. When the plan changes, edit this file — don't let the README and the code drift again.
