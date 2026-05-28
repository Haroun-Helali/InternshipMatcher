"""End-to-end happy path: upload a PDF, wait for indexing, query, assert answer + sources.

Requires Ollama running with both llama3.2 and mxbai-embed-large pulled.
Run with `pytest -m integration`.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app
from backend.app.services.document_store import (
    get_document_store,
    reset_document_store_for_tests,
)
from backend.app.services.vector_store import get_vector_store

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_internship.pdf"


@pytest.fixture(autouse=True, scope="module")
def _isolate_document_store(tmp_path_factory):
    """Point the document store at a tmpdir so tests don't touch repo state."""
    db = tmp_path_factory.mktemp("docstore") / "documents.sqlite"
    settings = get_settings()
    original = settings.document_db_path
    settings.document_db_path = str(db)
    reset_document_store_for_tests()
    # Force creation so subsequent get_document_store() calls reuse this DB.
    get_document_store()
    yield
    settings.document_db_path = original
    reset_document_store_for_tests()


@pytest.fixture
def client():
    return TestClient(app)


def _delete_all(client: TestClient) -> None:
    """Wipe every chunk in the vector store and every row in the SQLite store.

    ChromaDB persists to ./chroma_data on disk and is shared with any other
    backend process pointed at the same directory, so we have to clear by
    chunk-id directly — iterating /documents would miss orphan chunks left
    by other processes.

    We avoid `vector_store.clear_collection()` because that drops + recreates
    the underlying ChromaDB collection, leaving singleton references pointing
    at the old (deleted) collection UUID and the next query fails with
    InvalidCollectionException.
    """
    vstore = get_vector_store()
    try:
        ids = vstore.collection.get(include=[])["ids"]
    except Exception:
        ids = []
    if ids:
        try:
            vstore.collection.delete(ids=ids)
        except Exception:
            pass

    get_document_store().clear()


@pytest.fixture(autouse=True)
def clean_corpus(client: TestClient):
    _delete_all(client)
    yield
    _delete_all(client)


def _wait_for_indexing(client: TestClient, document_id: str, timeout_s: float = 60.0) -> int:
    """Poll the per-document status endpoint until processing settles.

    Background tasks fire after the upload response is sent, so we have to wait.
    Returns the number of chunks indexed. Raises if the doc enters FAILED state.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get(f"/api/v1/documents/{document_id}/status")
        if r.status_code == 200:
            body = r.json()
            state = body["state"]
            if state == "ready":
                return body["chunks_indexed"]
            if state == "failed":
                raise AssertionError(
                    f"Document {document_id} processing failed: {body.get('error')}"
                )
        time.sleep(0.5)
    raise AssertionError(
        f"Document {document_id} never finished indexing within {timeout_s}s"
    )


@pytest.mark.integration
def test_upload_then_query_returns_answer_and_sources(client: TestClient) -> None:
    # Upload
    with FIXTURE.open("rb") as f:
        upload = client.post(
            "/api/v1/documents/upload",
            files={"file": (FIXTURE.name, f, "application/pdf")},
        )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["success"] is True
    document_id = body["document_id"]
    assert document_id

    chunks = _wait_for_indexing(client, document_id)
    assert chunks > 0

    # The document_id returned by /upload must match what shows up downstream.
    listing = client.get("/api/v1/documents/").json()
    assert any(d["document_id"] == document_id for d in listing["documents"]), (
        f"document {document_id} not in listing {listing}"
    )

    # Query the corpus
    query = client.post(
        "/api/v1/query/",
        json={
            "question": "What internship is described in the document?",
            "session_id": "e2e-test",
            "top_k": 3,
        },
    )
    assert query.status_code == 200, query.text
    result = query.json()
    assert result["answer"]
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) >= 1
    src = result["sources"][0]
    assert src["document_id"] == document_id
    assert src["page_number"] >= 0
    assert src["content_preview"]


@pytest.mark.integration
def test_upload_status_progresses_to_ready(client: TestClient) -> None:
    """The status endpoint should reflect each lifecycle step."""
    with FIXTURE.open("rb") as f:
        body = client.post(
            "/api/v1/documents/upload",
            files={"file": (FIXTURE.name, f, "application/pdf")},
        ).json()
    document_id = body["document_id"]

    # Right after /upload, state is pending or processing — never 404.
    first = client.get(f"/api/v1/documents/{document_id}/status")
    assert first.status_code == 200, first.text
    assert first.json()["state"] in {"pending", "processing", "ready"}

    chunks = _wait_for_indexing(client, document_id)
    assert chunks > 0

    final = client.get(f"/api/v1/documents/{document_id}/status").json()
    assert final["state"] == "ready"
    assert final["chunks_indexed"] == chunks
    assert final["error"] is None
    assert final["filename"] == FIXTURE.name


@pytest.mark.integration
def test_status_endpoint_returns_404_for_unknown_document(client: TestClient) -> None:
    r = client.get("/api/v1/documents/not-a-real-doc-id/status")
    assert r.status_code == 404


@pytest.mark.integration
def test_query_with_empty_corpus_returns_graceful_message(client: TestClient) -> None:
    response = client.post(
        "/api/v1/query/",
        json={"question": "Anything?", "session_id": "empty"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"]
    assert body["sources"] == []
