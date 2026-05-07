"""Tests for report generator."""

import json
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.report_generator import generate_report

_mock_weasyprint = MagicMock()
sys.modules.setdefault("weasyprint", _mock_weasyprint)


def _make_finding(**overrides):
    f = MagicMock()
    f.id = overrides.get("id", uuid.uuid4())
    f.severity = MagicMock()
    f.severity.value = overrides.get("severity", "high")
    f.category = overrides.get("category", "sql-injection")
    f.title = overrides.get("title", "SQL Injection")
    f.file_path = overrides.get("file_path", "app/auth.py")
    f.line_start = overrides.get("line_start", 10)
    f.line_end = overrides.get("line_end", 15)
    f.description = overrides.get("description", "User input passed to query")
    f.regression_status = MagicMock()
    f.regression_status.value = overrides.get("regression_status", "new")
    f.fingerprint = overrides.get("fingerprint", "abc123")
    return f


@patch("app.services.report_generator.FindingRepository")
async def test_generate_markdown(mock_repo_cls: MagicMock) -> None:
    findings = [_make_finding(), _make_finding(severity="low", title="Info leak")]
    mock_repo_cls.return_value.list_by_session = AsyncMock(return_value=findings)

    session = AsyncMock()
    sid = uuid.uuid4()
    content, ctype, fname = await generate_report(session, sid, "markdown")

    assert ctype == "text/markdown"
    assert fname.endswith(".md")
    assert "SQL Injection" in content
    assert "Info leak" in content
    assert "HIGH" in content


@patch("app.services.report_generator.FindingRepository")
async def test_generate_csv(mock_repo_cls: MagicMock) -> None:
    findings = [_make_finding()]
    mock_repo_cls.return_value.list_by_session = AsyncMock(return_value=findings)

    session = AsyncMock()
    content, ctype, fname = await generate_report(session, uuid.uuid4(), "csv")

    assert ctype == "text/csv"
    assert fname.endswith(".csv")
    assert "severity" in content
    assert "sql-injection" in content


@patch("app.services.report_generator.FindingRepository")
async def test_generate_json(mock_repo_cls: MagicMock) -> None:
    findings = [_make_finding()]
    mock_repo_cls.return_value.list_by_session = AsyncMock(return_value=findings)

    session = AsyncMock()
    content, ctype, fname = await generate_report(session, uuid.uuid4(), "json")

    assert ctype == "application/json"
    assert fname.endswith(".json")
    data = json.loads(content)
    assert len(data) == 1
    assert data[0]["severity"] == "high"


@patch("app.services.report_generator.FindingRepository")
async def test_generate_pdf(mock_repo_cls: MagicMock) -> None:
    findings = [_make_finding()]
    mock_repo_cls.return_value.list_by_session = AsyncMock(return_value=findings)

    mock_html = MagicMock()
    mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
    _mock_weasyprint.HTML = mock_html

    session = AsyncMock()
    content, ctype, fname = await generate_report(session, uuid.uuid4(), "pdf")

    assert ctype == "application/pdf"
    assert fname.endswith(".pdf")
    assert content == b"%PDF-1.4 fake"
    mock_html.assert_called_once()
    call_kwargs = mock_html.call_args
    assert "SQL Injection" in call_kwargs.kwargs["string"]


@patch("app.services.report_generator.FindingRepository")
async def test_generate_empty_findings(mock_repo_cls: MagicMock) -> None:
    mock_repo_cls.return_value.list_by_session = AsyncMock(return_value=[])

    session = AsyncMock()
    content, ctype, fname = await generate_report(session, uuid.uuid4(), "json")

    data = json.loads(content)
    assert data == []
