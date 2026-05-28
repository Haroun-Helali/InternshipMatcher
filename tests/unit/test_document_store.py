"""Unit tests for the SQLite-backed document store."""
from datetime import datetime
from pathlib import Path

import pytest

from backend.app.models.api import DocumentStatusValue
from backend.app.services.document_store import DocumentStore


@pytest.fixture
def store(tmp_path: Path) -> DocumentStore:
    return DocumentStore(tmp_path / "documents.sqlite")


def test_insert_pending_creates_a_status_row(store: DocumentStore):
    store.insert_pending("doc-1", "resume.pdf")

    status = store.get_status("doc-1")
    assert status is not None
    assert status["state"] == DocumentStatusValue.PENDING
    assert status["filename"] == "resume.pdf"
    assert status["chunks_indexed"] == 0
    assert status["error"] is None
    assert isinstance(status["updated_at"], datetime)


def test_mark_processing_then_ready(store: DocumentStore):
    store.insert_pending("doc-1", "resume.pdf")
    store.mark_processing("doc-1")
    store.mark_ready(
        "doc-1",
        file_size=1024,
        page_count=3,
        document_type="pdf",
        chunk_count=5,
        created_at="2026-05-28T12:00:00+00:00",
    )

    status = store.get_status("doc-1")
    assert status["state"] == DocumentStatusValue.READY
    assert status["chunks_indexed"] == 5
    assert status["error"] is None

    rows = store.list_ready_metadata()
    assert len(rows) == 1
    assert rows[0]["document_id"] == "doc-1"
    assert rows[0]["file_size"] == 1024
    assert rows[0]["chunk_count"] == 5


def test_mark_failed_captures_error_and_keeps_doc_out_of_listing(store: DocumentStore):
    store.insert_pending("doc-1", "broken.pdf")
    store.mark_failed("doc-1", error="bad magic bytes")

    status = store.get_status("doc-1")
    assert status["state"] == DocumentStatusValue.FAILED
    assert status["error"] == "bad magic bytes"

    # FAILED documents shouldn't appear in /documents listings — only READY ones.
    assert store.list_ready_metadata() == []


def test_list_ready_metadata_skips_pending_and_processing(store: DocumentStore):
    store.insert_pending("pending-doc", "p.pdf")
    store.insert_pending("processing-doc", "q.pdf")
    store.mark_processing("processing-doc")
    store.insert_pending("ready-doc", "r.pdf")
    store.mark_ready(
        "ready-doc",
        file_size=10,
        page_count=1,
        document_type="pdf",
        chunk_count=1,
        created_at="2026-05-28T12:00:00+00:00",
    )

    rows = store.list_ready_metadata()
    ids = [r["document_id"] for r in rows]
    assert ids == ["ready-doc"]


def test_stats_only_counts_ready_docs(store: DocumentStore):
    store.insert_pending("a", "a.pdf")
    store.mark_ready(
        "a", file_size=100, page_count=1, document_type="pdf",
        chunk_count=2, created_at="2026-05-28T12:00:00+00:00",
    )
    store.insert_pending("b", "b.pdf")
    store.mark_ready(
        "b", file_size=300, page_count=2, document_type="pdf",
        chunk_count=8, created_at="2026-05-28T12:00:00+00:00",
    )
    store.insert_pending("c-pending", "c.pdf")

    s = store.stats()
    assert s["total_documents"] == 2
    assert s["total_size_bytes"] == 400
    assert s["total_chunks"] == 10


def test_delete_removes_status_and_metadata(store: DocumentStore):
    store.insert_pending("doc-1", "r.pdf")
    store.mark_ready(
        "doc-1", file_size=10, page_count=1, document_type="pdf",
        chunk_count=1, created_at="2026-05-28T12:00:00+00:00",
    )
    assert store.exists("doc-1")
    store.delete("doc-1")
    assert not store.exists("doc-1")
    assert store.get_status("doc-1") is None
    assert store.list_ready_metadata() == []


def test_clear_wipes_all_rows(store: DocumentStore):
    store.insert_pending("a", "a.pdf")
    store.insert_pending("b", "b.pdf")
    store.clear()
    assert store.get_status("a") is None
    assert store.get_status("b") is None


def test_get_status_returns_none_for_unknown_id(store: DocumentStore):
    assert store.get_status("never-uploaded") is None


def test_persists_across_instances(tmp_path: Path):
    """A second DocumentStore pointed at the same file sees prior writes."""
    db = tmp_path / "documents.sqlite"
    s1 = DocumentStore(db)
    s1.insert_pending("doc-1", "r.pdf")

    s2 = DocumentStore(db)
    status = s2.get_status("doc-1")
    assert status is not None
    assert status["state"] == DocumentStatusValue.PENDING
