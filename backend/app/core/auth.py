"""API key authentication middleware.

When `settings.api_key` is set, every request outside the open-path allowlist
must present `X-API-Key: <key>`. WebSocket clients send the key via the
`?api_key=<key>` query parameter (browsers can't set custom headers on the
WebSocket handshake).

Leave the setting empty in dev to disable auth.
"""
from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from backend.app.core.config import Settings

OPEN_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/files/",
)


def _is_open_path(path: str, settings: Settings) -> bool:
    if any(path == p or path.startswith(p) for p in OPEN_PATH_PREFIXES):
        return True
    # FastAPI docs always open — useful even in protected environments.
    docs_paths = (
        f"{settings.api_v1_prefix}/docs",
        f"{settings.api_v1_prefix}/redoc",
        f"{settings.api_v1_prefix}/openapi.json",
    )
    return path in docs_paths


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate `X-API-Key` on every non-open HTTP request.

    WebSocket connections bypass this middleware (Starlette only invokes
    BaseHTTPMiddleware for `http` scope); WS auth is enforced inside the
    WebSocket handler via `verify_websocket_api_key`.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._settings.api_key:
            return await call_next(request)
        if _is_open_path(request.url.path, self._settings):
            return await call_next(request)
        provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if provided != self._settings.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid API key"},
            )
        return await call_next(request)


def verify_websocket_api_key(websocket, settings: Settings) -> bool:
    """Return True if the WS handshake passes auth (or auth is disabled).

    The caller is responsible for closing the socket with code 4401 when
    this returns False — we can't do it here without awaiting.
    """
    if not settings.api_key:
        return True
    provided = (
        websocket.headers.get("x-api-key")
        or websocket.query_params.get("api_key")
    )
    return provided == settings.api_key


def install_api_key_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(APIKeyMiddleware, settings=settings)
