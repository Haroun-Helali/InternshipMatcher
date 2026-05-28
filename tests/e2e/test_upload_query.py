"""End-to-end happy path: upload a PDF, wait for indexing, query, assert answer + sources.

Requires Ollama running with both llama3.2 and mxbai-embed-large pulled.
Run with `pytest -m integration`.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_internship.pdf"


@pytest.fixture
def client():
    return TestClient(app)


def _delete_all(client: TestClient) -> None:
    """Remove every indexed document via the public API.

    Avoids `vector_store.clear_collection()` because that drops + recreates the
    underlying ChromaDB collection, which leaves singleton references pointing
    at the old (deleted) collection UUID and the next query fails with
    InvalidCollectionException.
    """
    listing = client.get("/api/v1/documents/").json()
    for doc in listing.get("documents", []):
        client.delete(f"/api/v1/documents/{doc['document_id']}")


@pytest.fixture(autouse=True)
def clean_corpus(client: TestClient):
    _delete_all(client)
    yield
    _delete_all(client)


def _wait_for_indexing(client: TestClient, document_id: str, timeout_s: float = 60.0) -> int:
    """Poll the stats endpoint until at least one chunk lands in the vector store.

    Background tasks fire after the upload response is sent, so we have to wait.
    Returns the number of chunks indexed.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        stats = client.get("/api/v1/documents/stats").json()
        if stats["total_chunks"] > 0:
            return stats["total_chunks"]
        time.sleep(1.0)
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
    # Note: the upload returns one document_id but the document_processor mints
    # its own internal ID (see docs/ROADMAP.md Phase B — ID consistency bug).
    # Match by filename until that's fixed.
    assert body["document_id"]

    chunks = _wait_for_indexing(client, body["document_id"])
    assert chunks > 0

    # The processed document should appear in the listing under the filename.
    listing = client.get("/api/v1/documents/").json()
    matches = [d for d in listing["documents"] if d["filename"] == FIXTURE.name]
    assert matches, f"sample_internship.pdf not found in {listing}"
    indexed_id = matches[0]["document_id"]

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
    assert src["document_id"] == indexed_id
    assert src["page_number"] >= 0
    assert src["content_preview"]


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
