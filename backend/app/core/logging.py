"""Logging configuration.

Supports both classic text logs (default) and JSON-line logs (set
`LOG_FORMAT=json` in `.env`). All records carry the current request ID — set
by `RequestIDMiddleware` on inbound HTTP requests and propagated via a
`contextvars.ContextVar` so async tasks inherit it.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Optional

from backend.app.core.config import get_settings

# `-` is what shows up in logs emitted outside of a request (startup, CLI).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIDFilter(logging.Filter):
    """Inject `request_id` from the contextvar onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    """One-line JSON formatter for ingestion by log shippers."""

    _STANDARD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Carry any `extra={...}` fields through verbatim.
        for key, value in record.__dict__.items():
            if key in self._STANDARD_ATTRS or key in payload or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure root logging based on settings.

    `LOG_FORMAT=json` switches to one-line JSON output on both handlers.
    Anything else is treated as a classic logging format string.
    """
    settings = get_settings()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    use_json = settings.log_format.strip().lower() == "json"
    formatter: logging.Formatter = (
        _JsonFormatter()
        if use_json
        else logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s"
        )
    )
    request_id_filter = _RequestIDFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(request_id_filter)

    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(request_id_filter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    # Replace any handlers installed by a prior call (reload / tests).
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(value: Optional[str]) -> str:
    """Bind the current request id (generating one if not provided)."""
    rid = value or new_request_id()
    request_id_var.set(rid)
    return rid
