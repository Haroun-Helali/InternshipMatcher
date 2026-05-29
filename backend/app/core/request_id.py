"""Request-ID middleware.

Reads `X-Request-ID` from the inbound request when present (so callers can
correlate across services) or generates a new one. Echoes the value back as
a response header and binds it to the logging contextvar for the duration
of the request.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.logging import set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = set_request_id(incoming)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
