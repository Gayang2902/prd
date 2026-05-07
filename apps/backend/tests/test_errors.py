"""Tests for RFC 7807 error handling."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers


def _make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/not-found")
    def not_found():
        raise HTTPException(status_code=404, detail="Item not found")

    @app.get("/crash")
    def crash():
        raise RuntimeError("boom")

    return app


def test_normal_response_unchanged() -> None:
    client = TestClient(_make_app())
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_http_exception_returns_problem_json() -> None:
    client = TestClient(_make_app())
    resp = client.get("/not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Item not found"
    assert body["status"] == 404


def test_unhandled_exception_returns_500_problem() -> None:
    client = TestClient(_make_app(), raise_server_exceptions=False)
    resp = client.get("/crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["type"] == "about:blank"
    assert body["title"] == "Internal Server Error"
    assert body["status"] == 500
