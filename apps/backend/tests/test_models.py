"""Tests for model enums and basic model properties."""

from app.models.analysis_session import SessionPriority, SessionState
from app.models.finding import RegressionStatus, Severity
from app.models.user import Role


def test_session_state_values() -> None:
    assert SessionState.QUEUED.value == "queued"
    assert SessionState.COMPLETED.value == "completed"
    assert SessionState.FAILED.value == "failed"
    assert SessionState.CANCELED.value == "canceled"


def test_session_priority_values() -> None:
    assert SessionPriority.URGENT.value == "urgent"
    assert SessionPriority.NORMAL.value == "normal"
    assert SessionPriority.BACKGROUND.value == "background"


def test_severity_ordering() -> None:
    severities = [s.value for s in Severity]
    assert "critical" in severities
    assert "info" in severities


def test_regression_status_values() -> None:
    assert RegressionStatus.NEW.value == "new"
    assert RegressionStatus.RECURRING.value == "recurring"
    assert RegressionStatus.RESOLVED.value == "resolved"
    assert RegressionStatus.CARRIED_OVER.value == "carried_over"


def test_role_hierarchy() -> None:
    from app.auth.dependencies import ROLE_HIERARCHY

    assert ROLE_HIERARCHY[Role.VIEWER] < ROLE_HIERARCHY[Role.REVIEWER]
    assert ROLE_HIERARCHY[Role.REVIEWER] < ROLE_HIERARCHY[Role.LEAD]
    assert ROLE_HIERARCHY[Role.LEAD] < ROLE_HIERARCHY[Role.ADMIN]


def test_state_transitions_defined() -> None:
    from app.services.repositories.session import VALID_TRANSITIONS

    assert SessionState.PREPARING in VALID_TRANSITIONS[SessionState.QUEUED]
    assert SessionState.CANCELED in VALID_TRANSITIONS[SessionState.QUEUED]
    assert len(VALID_TRANSITIONS[SessionState.COMPLETED]) == 0
    assert len(VALID_TRANSITIONS[SessionState.FAILED]) == 0
