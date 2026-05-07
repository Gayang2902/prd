"""Simple in-memory rate limiter middleware.

Uses a sliding window per user (X-User-Id header) or per IP as fallback.
For production, replace with Redis-backed implementation.
"""

import time
from collections import defaultdict

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

DEFAULT_REQUESTS_PER_MINUTE = 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.window = 60.0
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        user_id = request.headers.get("x-user-id")
        if user_id:
            return f"user:{user_id}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = self._client_key(request)
        now = time.monotonic()
        cutoff = now - self.window

        timestamps = self._hits[key]
        self._hits[key] = [t for t in timestamps if t > cutoff]

        if len(self._hits[key]) >= self.rpm:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Rate limit exceeded: {self.rpm} requests per minute",
                },
                media_type="application/problem+json",
            )

        self._hits[key].append(now)
        return await call_next(request)
