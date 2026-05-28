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

- [x] **Document ID consistency**. The upload endpoint generated one `document_id` but `doc_processor.process_pdf` minted its own. Threaded the upload ID through; e2e test now asserts the API-returned ID matches the listing + query sources.
- [x] **Server-side match extraction**. `QueryResponse` now carries `matches: List[Match]` parsed by `backend/app/services/match_parser.py`. The WS stream emits a `matches` event with a `cleaned_answer`. Frontend regex parser is gone.
- [x] **Upload status endpoint**. `GET /api/v1/documents/{id}/status` returns `{state: pending|processing|ready|failed, chunks_indexed, error}`.
- [x] **SQLite metadata store**. `backend/app/services/document_store.py` wraps a single `documents` table keyed by `document_id` with both metadata and lifecycle status. Survives backend restarts; verified manually with an upload → restart → list cycle.
- [x] **Dependency refresh**. `chromadb 0.4.22 → 1.5.9`, `langchain-text-splitters 0.0.1 → 1.1.2`, `ollama 0.1.6 → 0.6.2`, `fastapi 0.104.1 → 0.136.3`, `pydantic 2.5.0 → 2.13.4`. All tests still pass.
- [x] **Ruff cleanup**. 445 → 0 violations after `ruff --fix` plus 17 manual `raise ... from e` patches and a handful of `# noqa` on intentional late imports. CI ruff check is now required (no `continue-on-error`).

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
