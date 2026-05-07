"""Tests for API endpoints with mocked dependencies."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.main import app
from app.models.analysis_session import SessionPriority, SessionState
from app.models.finding import RegressionStatus, Severity
from app.models.finding_status import VerificationStatus
from app.models.project import Priority, ProjectStatus
from app.models.user import Role

_NOW = datetime(2026, 5, 7, 12, 0, 0, tzinfo=UTC)


def _mock_user(**overrides):
    u = MagicMock()
    u.id = overrides.get("id", uuid.uuid4())
    u.email = overrides.get("email", "test@example.com")
    u.name = overrides.get("name", "Test User")
    u.role = overrides.get("role", Role.ADMIN)
    u.created_at = _NOW
    u.updated_at = _NOW
    return u


def _mock_project(**overrides):
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.name = overrides.get("name", "TestProject")
    p.gitlab_project_id = overrides.get("gitlab_project_id", "123")
    p.owner_id = overrides.get("owner_id", uuid.uuid4())
    p.priority = overrides.get("priority", Priority.NORMAL)
    p.status = overrides.get("status", ProjectStatus.PENDING)
    p.deadline = overrides.get("deadline")
    p.created_at = _NOW
    p.updated_at = _NOW
    return p


def _mock_preset(**overrides):
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.name = overrides.get("name", "Default")
    p.agent_id = overrides.get("agent_id", uuid.uuid4())
    p.version_sha = overrides.get("version_sha", "abc123")
    p.prompt_template = overrides.get("prompt_template", "")
    p.ruleset = overrides.get("ruleset", {})
    p.timeout_seconds = overrides.get("timeout_seconds", 1800)
    p.max_retries = overrides.get("max_retries", 3)
    p.is_shared = overrides.get("is_shared", False)
    p.created_at = _NOW
    p.updated_at = _NOW
    return p


def _mock_session(**overrides):
    s = MagicMock()
    s.id = overrides.get("id", uuid.uuid4())
    s.project_id = overrides.get("project_id", uuid.uuid4())
    s.commit_sha = overrides.get("commit_sha", "abc1234")
    s.agent_id = overrides.get("agent_id", uuid.uuid4())
    s.preset_id = overrides.get("preset_id", uuid.uuid4())
    s.model_version = overrides.get("model_version", "test-v1")
    s.container_image_sha = overrides.get("container_image_sha")
    s.state = overrides.get("state", SessionState.QUEUED)
    s.priority = overrides.get("priority", SessionPriority.NORMAL)
    s.started_at = _NOW
    s.completed_at = overrides.get("completed_at")
    s.token_usage = overrides.get("token_usage", 0)
    s.cost = overrides.get("cost", Decimal("0"))
    return s


def _mock_finding(**overrides):
    f = MagicMock()
    f.id = overrides.get("id", uuid.uuid4())
    f.session_id = overrides.get("session_id", uuid.uuid4())
    f.fingerprint = overrides.get("fingerprint", "fp123")
    f.file_path = overrides.get("file_path", "app/main.py")
    f.line_start = overrides.get("line_start", 1)
    f.line_end = overrides.get("line_end", 5)
    f.severity = overrides.get("severity", Severity.HIGH)
    f.category = overrides.get("category", "xss")
    f.title = overrides.get("title", "XSS Vulnerability")
    f.description = overrides.get("description", "Reflected XSS")
    f.regression_status = overrides.get("regression_status", RegressionStatus.NEW)
    f.created_at = _NOW
    f.updated_at = _NOW
    return f


def _setup_overrides(mock_user=None):
    mock_db = AsyncMock()
    user = mock_user or _mock_user()

    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    return mock_db, user


def _cleanup():
    app.dependency_overrides.clear()


# ── Projects ──


def test_list_projects() -> None:
    from app.api.v1.projects import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list.return_value = [_mock_project()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    _cleanup()


def test_get_project_not_found() -> None:
    from app.api.v1.projects import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert resp.status_code == 404
    _cleanup()


def test_get_project_found() -> None:
    from app.api.v1.projects import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_project()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "TestProject"
    _cleanup()


def test_update_project() -> None:
    from app.api.v1.projects import _get_repo

    proj = _mock_project()
    mock_repo = AsyncMock()
    mock_repo.get.return_value = proj
    mock_repo.update.return_value = proj
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"name": "Updated"})
    assert resp.status_code == 200
    _cleanup()


def test_update_project_not_found() -> None:
    from app.api.v1.projects import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"name": "Nope"})
    assert resp.status_code == 404
    _cleanup()


def test_create_project() -> None:
    from app.api.v1.projects import _get_repo

    proj = _mock_project()
    mock_repo = AsyncMock()
    mock_repo.create.return_value = proj
    app.dependency_overrides[_get_repo] = lambda: mock_repo

    mock_user = _mock_user()
    mock_db, _ = _setup_overrides(mock_user)

    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.commit = AsyncMock()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/projects",
        json={"name": "New", "gitlab_project_id": "gl-1"},
    )
    assert resp.status_code == 201
    _cleanup()


def test_create_project_no_users() -> None:
    from app.api.v1.projects import _get_repo

    mock_repo = AsyncMock()
    app.dependency_overrides[_get_repo] = lambda: mock_repo

    mock_db, _ = _setup_overrides()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/projects",
        json={"name": "New", "gitlab_project_id": "gl-1"},
    )
    assert resp.status_code == 400
    _cleanup()


def test_regression_history() -> None:
    mock_db, _ = _setup_overrides()

    mock_sessions_result = MagicMock()
    session = _mock_session(state=SessionState.COMPLETED)
    mock_sessions_result.scalars.return_value.all.return_value = [session]

    mock_counts_result = MagicMock()
    mock_counts_result.all.return_value = [
        (RegressionStatus.NEW, 3),
        (RegressionStatus.RECURRING, 1),
    ]

    mock_db.execute = AsyncMock(side_effect=[mock_sessions_result, mock_counts_result])

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/projects/{uuid.uuid4()}/regression-history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["new"] == 3
    assert data[0]["recurring"] == 1
    assert data[0]["total"] == 4
    _cleanup()


# ── Presets ──


def test_list_presets() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list.return_value = [_mock_preset()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/presets")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    _cleanup()


def test_get_preset_not_found() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/presets/{uuid.uuid4()}")
    assert resp.status_code == 404
    _cleanup()


def test_get_preset_found() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_preset()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/presets/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Default"
    _cleanup()


def test_create_preset() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.create.return_value = _mock_preset()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/presets",
        json={
            "name": "New Preset",
            "agent_id": str(uuid.uuid4()),
            "version_sha": "xyz789",
        },
    )
    assert resp.status_code == 201
    _cleanup()


def test_update_preset() -> None:
    from app.api.v1.presets import _get_repo

    preset = _mock_preset()
    mock_repo = AsyncMock()
    mock_repo.get.return_value = preset
    mock_repo.update.return_value = preset
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.patch(f"/api/v1/presets/{uuid.uuid4()}", json={"name": "Updated"})
    assert resp.status_code == 200
    _cleanup()


def test_delete_preset() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_preset()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.delete(f"/api/v1/presets/{uuid.uuid4()}")
    assert resp.status_code == 204
    _cleanup()


def test_delete_preset_not_found() -> None:
    from app.api.v1.presets import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.delete(f"/api/v1/presets/{uuid.uuid4()}")
    assert resp.status_code == 404
    _cleanup()


# ── Sessions ──


def test_list_sessions() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list_by_project.return_value = [_mock_session()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/projects/{uuid.uuid4()}/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    _cleanup()


def test_get_session_not_found() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
    _cleanup()


def test_get_session_found() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_session()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 200
    _cleanup()


def test_cancel_session() -> None:
    from app.api.v1.sessions import _get_repo

    sess = _mock_session()
    mock_repo = AsyncMock()
    mock_repo.get.return_value = sess
    mock_repo.transition.return_value = sess
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/cancel")
    assert resp.status_code == 200
    _cleanup()


def test_cancel_session_not_found() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/cancel")
    assert resp.status_code == 404
    _cleanup()


def test_stream_session_logs() -> None:
    from app.api.v1.sessions import _get_repo

    sess = _mock_session(state=SessionState.COMPLETED)
    mock_repo = AsyncMock()
    mock_repo.get.return_value = sess
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}/logs")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    _cleanup()


# ── Queue ──


def test_list_queue() -> None:
    from app.api.v1.queue import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list_queue.return_value = [_mock_session()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/queue")
    assert resp.status_code == 200
    _cleanup()


# ── Users ──


def test_get_me() -> None:
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"
    _cleanup()


def test_list_users() -> None:
    from app.api.v1.users import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list.return_value = [_mock_user()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/users")
    assert resp.status_code == 200
    _cleanup()


def test_create_user_duplicate() -> None:
    from app.api.v1.users import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get_by_email.return_value = _mock_user()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "name": "Test",
            "role": "viewer",
        },
    )
    assert resp.status_code == 409
    _cleanup()


# ── Findings ──


def test_list_findings() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.list_by_session.return_value = [_mock_finding()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}/findings")
    assert resp.status_code == 200
    _cleanup()


# ── Usage ──


def test_cost_summary() -> None:
    from unittest.mock import patch

    mock_db = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _mock_user()

    with patch(
        "app.api.v1.usage.cost_summary",
        new=AsyncMock(
            return_value={
                "total_sessions": 10,
                "total_tokens": 5000,
                "total_cost": Decimal("12.50"),
            }
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/usage/cost")
        assert resp.status_code == 200
        assert resp.json()["total_sessions"] == 10

    app.dependency_overrides.clear()


# ── More Findings ──


def _mock_finding_status(**overrides):
    fs = MagicMock()
    fs.id = overrides.get("id", uuid.uuid4())
    fs.finding_id = overrides.get("finding_id", uuid.uuid4())
    fs.changed_by = overrides.get("changed_by", uuid.uuid4())
    fs.status = overrides.get("status", VerificationStatus.OPEN)
    fs.reason = overrides.get("reason")
    fs.changed_at = _NOW
    return fs


def _mock_comment(**overrides):
    c = MagicMock()
    c.id = overrides.get("id", uuid.uuid4())
    c.finding_id = overrides.get("finding_id", uuid.uuid4())
    c.author_id = overrides.get("author_id", uuid.uuid4())
    c.content = overrides.get("content", "Looks like a real issue")
    c.created_at = _NOW
    return c


def test_get_finding_found() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_finding()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/findings/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "XSS Vulnerability"
    _cleanup()


def test_get_finding_not_found() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/findings/{uuid.uuid4()}")
    assert resp.status_code == 404
    _cleanup()


def test_update_finding_status() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_finding()
    mock_repo.add_status.return_value = _mock_finding_status(status=VerificationStatus.CONFIRMED)
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.patch(
        f"/api/v1/findings/{uuid.uuid4()}/status",
        json={
            "status": "confirmed",
            "reason": "Verified manually",
        },
    )
    assert resp.status_code == 200
    _cleanup()


def test_update_finding_status_not_found() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.patch(
        f"/api/v1/findings/{uuid.uuid4()}/status",
        json={
            "status": "confirmed",
        },
    )
    assert resp.status_code == 404
    _cleanup()


def test_get_finding_timeline() -> None:
    from app.api.v1.findings import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get_status_history.return_value = [_mock_finding_status()]
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/findings/{uuid.uuid4()}/timeline")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    _cleanup()


def test_list_comments() -> None:
    from app.api.v1.findings import _get_comment_repo

    mock_repo = AsyncMock()
    mock_repo.list_by_finding.return_value = [_mock_comment()]
    app.dependency_overrides[_get_comment_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/findings/{uuid.uuid4()}/comments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    _cleanup()


def test_create_comment() -> None:
    from app.api.v1.findings import _get_comment_repo

    mock_repo = AsyncMock()
    mock_repo.create.return_value = _mock_comment()
    app.dependency_overrides[_get_comment_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        f"/api/v1/findings/{uuid.uuid4()}/comments",
        json={
            "content": "This needs fixing",
        },
    )
    assert resp.status_code == 201
    _cleanup()


# ── Audit ──


def test_list_audit_logs() -> None:
    from unittest.mock import patch

    mock_log = MagicMock()
    mock_log.id = uuid.uuid4()
    mock_log.user_id = uuid.uuid4()
    mock_log.action = "create"
    mock_log.resource_type = "project"
    mock_log.resource_id = str(uuid.uuid4())
    mock_log.detail = None
    mock_log.ip_address = "127.0.0.1"
    mock_log.created_at = _NOW

    _setup_overrides()

    with patch("app.api.v1.audit.list_audit_logs", new=AsyncMock(return_value=[mock_log])):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/audit/logs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    _cleanup()


# ── More Usage ──


# ── Reports ──


def test_create_report() -> None:
    from unittest.mock import patch

    _setup_overrides()

    with patch(
        "app.api.v1.reports.generate_report",
        new=AsyncMock(return_value=("# Report", "text/markdown", "report_abc_20260507.md")),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/reports?format=markdown")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]

    _cleanup()


def test_create_report_csv() -> None:
    from unittest.mock import patch

    _setup_overrides()

    with patch(
        "app.api.v1.reports.generate_report",
        new=AsyncMock(
            return_value=("severity,title\nhigh,XSS", "text/csv", "report_abc_20260507.csv")
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/reports?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    _cleanup()


def test_cost_by_project() -> None:
    from unittest.mock import patch

    _setup_overrides()

    with patch(
        "app.api.v1.usage.cost_by_project",
        new=AsyncMock(
            return_value=[
                {
                    "project_id": str(uuid.uuid4()),
                    "sessions": 5,
                    "tokens": 2000,
                    "cost": Decimal("5.00"),
                }
            ]
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/usage/by-project")
        assert resp.status_code == 200

    _cleanup()


def test_cost_by_agent() -> None:
    from unittest.mock import patch

    _setup_overrides()

    with patch(
        "app.api.v1.usage.cost_by_agent",
        new=AsyncMock(
            return_value=[
                {"model_version": "test-v1", "sessions": 3, "tokens": 1000, "cost": Decimal("3.00")}
            ]
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/usage/by-agent")
        assert resp.status_code == 200

    _cleanup()


def test_cost_daily() -> None:
    from unittest.mock import patch

    _setup_overrides()

    with patch(
        "app.api.v1.usage.cost_daily",
        new=AsyncMock(
            return_value=[
                {"date": "2026-05-07", "sessions": 2, "tokens": 500, "cost": Decimal("1.00")}
            ]
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/usage/daily")
        assert resp.status_code == 200

    _cleanup()


# ── Create Session ──


def test_create_session_no_agents() -> None:
    from unittest.mock import patch

    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    with patch("app.api.v1.sessions.get_registry", return_value={}):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            f"/api/v1/projects/{uuid.uuid4()}/sessions",
            json={
                "branch": "main",
                "commit_sha": "abc1234",
                "preset_id": str(uuid.uuid4()),
                "agent_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "No agents" in body.get("detail", body.get("title", ""))

    _cleanup()


def test_create_session_success() -> None:
    from unittest.mock import patch

    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.create.return_value = _mock_session()
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    fake_meta = MagicMock()
    fake_meta.name = "test-agent"
    fake_meta.version = "1.0"
    fake_agent = MagicMock()
    fake_agent.describe.return_value = fake_meta

    with patch("app.api.v1.sessions.get_registry", return_value={"test": fake_agent}):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            f"/api/v1/projects/{uuid.uuid4()}/sessions",
            json={
                "branch": "main",
                "commit_sha": "abc1234",
                "preset_id": str(uuid.uuid4()),
                "agent_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 202

    _cleanup()


def test_cancel_session_conflict() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = _mock_session()
    mock_repo.transition.side_effect = RuntimeError("Invalid transition")
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/sessions/{uuid.uuid4()}/cancel")
    assert resp.status_code == 409

    _cleanup()


def test_stream_session_logs_running() -> None:
    from app.api.v1.sessions import _get_repo

    sess = _mock_session(state=SessionState.RUNNING)
    mock_repo = AsyncMock()
    mock_repo.get.return_value = sess
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}/logs")
    assert resp.status_code == 200
    assert "event: state" in resp.text

    _cleanup()


def test_stream_session_logs_not_found() -> None:
    from app.api.v1.sessions import _get_repo

    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}/logs")
    assert resp.status_code == 404

    _cleanup()


# ── Create User success ──


def test_create_user_success() -> None:
    from app.api.v1.users import _get_repo

    new_user = _mock_user(email="new@example.com", name="New User")
    mock_repo = AsyncMock()
    mock_repo.get_by_email.return_value = None
    mock_repo.create.return_value = new_user
    app.dependency_overrides[_get_repo] = lambda: mock_repo
    _setup_overrides()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/users",
        json={
            "email": "new@example.com",
            "name": "New User",
            "role": "viewer",
        },
    )
    assert resp.status_code == 201

    _cleanup()
