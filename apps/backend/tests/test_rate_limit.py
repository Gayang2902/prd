"""Tests for rate limiting middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware


def _make_app(rpm: int = 5) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rpm)

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    return app


def test_allows_requests_under_limit() -> None:
    client = TestClient(_make_app(rpm=5))
    for _ in range(5):
        resp = client.get("/test")
        assert resp.status_code == 200


def test_blocks_requests_over_limit() -> None:
    client = TestClient(_make_app(rpm=3))
    for _ in range(3):
        resp = client.get("/test")
        assert resp.status_code == 200

    resp = client.get("/test")
    assert resp.status_code == 429
    assert resp.json()["title"] == "Too Many Requests"


def test_rate_limit_response_is_problem_json() -> None:
    client = TestClient(_make_app(rpm=1))
    client.get("/test")
    resp = client.get("/test")
    assert resp.status_code == 429
    body = resp.json()
    assert body["type"] == "about:blank"
    assert body["status"] == 429
