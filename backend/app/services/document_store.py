"""SQLite-backed persistence for document metadata and processing status.

Replaces the two in-process dicts (`documents_metadata`, `documents_status`)
that previously lived in `backend.app.api.documents`. Survives backend
restarts; ChromaDB still owns the vectors and chunks.

Schema is a single `documents` table — status is 1:1 with the document, so
folding it in keeps queries trivial. SQLite operations are blocking, which
is fine for our volume (handfuls of writes per upload, plus listing/status
polls). If we ever need true async, swap to `aiosqlite`.

This module is import-safe: it does not touch the filesystem until
`get_document_store()` is called.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import get_settings
from backend.app.models.api import DocumentStatusValue

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id        TEXT PRIMARY KEY,
    filename           TEXT NOT NULL,
    state              TEXT NOT NULL,
    chunks_indexed     INTEGER NOT NULL DEFAULT 0,
    error              TEXT,
    status_updated_at  TEXT NOT NULL,
    -- Populated by mark_ready; null until then.
    file_size          INTEGER,
    page_count         INTEGER,
    document_type      TEXT,
    chunk_count        INTEGER,
    created_at         TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentStore:
    """Thread-safe wrapper around a single SQLite file."""

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite connections are not safe to share across threads by default;
        # FastAPI's BackgroundTasks run on a threadpool, and TestClient runs
        # the app in the request thread. A single connection + a lock is
        # simpler than per-thread connections for this scale.
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit; we wrap multi-statement work in `with self._lock`
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
        logger.info("DocumentStore ready at %s", self._db_path)

    # ----- writes -----

    def insert_pending(self, document_id: str, filename: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO documents
                    (document_id, filename, state, chunks_indexed, error, status_updated_at)
                VALUES (?, ?, ?, 0, NULL, ?)
                """,
                (document_id, filename, DocumentStatusValue.PENDING.value, _now_iso()),
            )

    def mark_processing(self, document_id: str) -> None:
        self._update_state(document_id, DocumentStatusValue.PROCESSING, error=None)

    def mark_ready(
        self,
        document_id: str,
        *,
        file_size: int,
        page_count: int,
        document_type: str,
        chunk_count: int,
        created_at: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE documents
                SET state = ?,
                    chunks_indexed = ?,
                    error = NULL,
                    status_updated_at = ?,
                    file_size = ?,
                    page_count = ?,
                    document_type = ?,
                    chunk_count = ?,
                    created_at = ?
                WHERE document_id = ?
                """,
                (
                    DocumentStatusValue.READY.value,
                    chunk_count,
                    _now_iso(),
                    file_size,
                    page_count,
                    document_type,
                    chunk_count,
                    created_at,
                    document_id,
                ),
            )

    def mark_failed(self, document_id: str, error: str) -> None:
        self._update_state(document_id, DocumentStatusValue.FAILED, error=error)

    def delete(self, document_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM documents WHERE document_id = ?", (document_id,)
            )

    def clear(self) -> None:
        """Wipe every row. Intended for tests."""
        with self._lock:
            self._conn.execute("DELETE FROM documents")

    def _update_state(
        self,
        document_id: str,
        state: DocumentStatusValue,
        *,
        error: Optional[str],
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE documents
                SET state = ?, error = ?, status_updated_at = ?
                WHERE document_id = ?
                """,
                (state.value, error, _now_iso(), document_id),
            )

    # ----- reads -----

    def get_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        row = self._fetch_one(
            """
            SELECT document_id, filename, state, chunks_indexed, error,
                   status_updated_at
            FROM documents WHERE document_id = ?
            """,
            (document_id,),
        )
        if row is None:
            return None
        return {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "state": DocumentStatusValue(row["state"]),
            "chunks_indexed": row["chunks_indexed"],
            "error": row["error"],
            "updated_at": datetime.fromisoformat(row["status_updated_at"]),
        }

    def list_ready_metadata(self) -> List[Dict[str, Any]]:
        """Return the metadata rows for every document that finished processing.

        Documents still in pending/processing/failed are excluded — they
        don't have full metadata yet. The /status endpoint is the way to
        check on those.
        """
        rows = self._fetch_all(
            """
            SELECT document_id, filename, file_size, page_count, document_type,
                   chunk_count, created_at
            FROM documents
            WHERE state = ?
            ORDER BY created_at DESC
            """,
            (DocumentStatusValue.READY.value,),
        )
        return [
            {
                "document_id": r["document_id"],
                "filename": r["filename"],
                "file_size": r["file_size"],
                "page_count": r["page_count"],
                "document_type": r["document_type"],
                "chunk_count": r["chunk_count"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def stats(self) -> Dict[str, Any]:
        """Aggregate stats for the READY documents."""
        row = self._fetch_one(
            """
            SELECT COUNT(*)                AS total_documents,
                   COALESCE(SUM(file_size), 0) AS total_size_bytes,
                   COALESCE(SUM(chunk_count), 0) AS total_chunks
            FROM documents
            WHERE state = ?
            """,
            (DocumentStatusValue.READY.value,),
        )
        assert row is not None  # COUNT(*) always returns one row
        return {
            "total_documents": row["total_documents"],
            "total_size_bytes": row["total_size_bytes"],
            "total_chunks": row["total_chunks"],
        }

    def exists(self, document_id: str) -> bool:
        row = self._fetch_one(
            "SELECT 1 FROM documents WHERE document_id = ?", (document_id,)
        )
        return row is not None

    # ----- helpers -----

    def _fetch_one(self, sql: str, params: tuple) -> Optional[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()

    def _fetch_all(self, sql: str, params: tuple) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()


_store: Optional[DocumentStore] = None
_store_lock = threading.Lock()


def get_document_store() -> DocumentStore:
    """Return the process-wide DocumentStore singleton, creating it lazily."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = DocumentStore(get_settings().document_db_path)
    return _store


def reset_document_store_for_tests() -> None:
    """Drop the singleton so tests can swap in a temporary DB path."""
    global _store
    _store = None
