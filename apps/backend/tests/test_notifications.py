"""Tests for notification service."""

import uuid

import pytest

from app.services.notifications import (
    Notification,
    TriggerType,
    notify,
    notify_analysis_completed,
    notify_analysis_failed,
    notify_budget_threshold,
    notify_critical_finding,
    send_email,
    send_slack,
)


@pytest.fixture
def sample_notification() -> Notification:
    return Notification(
        trigger=TriggerType.ANALYSIS_COMPLETED,
        title="Test",
        body="Test body",
        project_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
    )


async def test_send_slack_skips_when_no_webhook(sample_notification: Notification) -> None:
    result = await send_slack(sample_notification)
    assert result is False


async def test_send_email_skips_when_no_smtp(sample_notification: Notification) -> None:
    result = await send_email(sample_notification, ["test@example.com"])
    assert result is False


async def test_notify_calls_both_channels(sample_notification: Notification) -> None:
    await notify(sample_notification)
    await notify(sample_notification, email_recipients=["a@b.com"])


async def test_notify_analysis_completed() -> None:
    await notify_analysis_completed(
        project_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        finding_count=5,
        cost="1.23",
    )


async def test_notify_analysis_failed() -> None:
    await notify_analysis_failed(
        project_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        reason="timeout",
    )


async def test_notify_budget_threshold() -> None:
    await notify_budget_threshold(current_cost="80.00", budget="100.00", percentage=80)


async def test_notify_critical_finding() -> None:
    await notify_critical_finding(
        project_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        finding_title="SQL Injection in auth.py",
    )


def test_trigger_type_values() -> None:
    assert TriggerType.ANALYSIS_COMPLETED.value == "analysis_completed"
    assert TriggerType.ANALYSIS_FAILED.value == "analysis_failed"
    assert TriggerType.BUDGET_THRESHOLD.value == "budget_threshold"
    assert TriggerType.FINDING_CRITICAL.value == "finding_critical"


def test_notification_dataclass() -> None:
    pid = uuid.uuid4()
    sid = uuid.uuid4()
    n = Notification(
        trigger=TriggerType.FINDING_CRITICAL,
        title="Title",
        body="Body",
        project_id=pid,
        session_id=sid,
    )
    assert n.trigger == TriggerType.FINDING_CRITICAL
    assert n.project_id == pid
    assert n.session_id == sid


def test_notification_defaults() -> None:
    n = Notification(trigger=TriggerType.BUDGET_THRESHOLD, title="T", body="B")
    assert n.project_id is None
    assert n.session_id is None


async def test_send_slack_with_webhook(sample_notification: Notification) -> None:
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_settings = MagicMock()
    mock_settings.slack_webhook_url = "https://hooks.slack.com/test"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.services.notifications.settings", mock_settings), \
         patch("httpx.AsyncClient", return_value=mock_client):
        result = await send_slack(sample_notification)
    assert result is True


async def test_send_slack_with_webhook_failure(sample_notification: Notification) -> None:
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_settings = MagicMock()
    mock_settings.slack_webhook_url = "https://hooks.slack.com/test"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("connection error"))

    with patch("app.services.notifications.settings", mock_settings), \
         patch("httpx.AsyncClient", return_value=mock_client):
        result = await send_slack(sample_notification)
    assert result is False


async def test_send_email_with_smtp(sample_notification: Notification) -> None:
    from unittest.mock import patch, MagicMock

    mock_settings = MagicMock()
    mock_settings.smtp_host = "smtp.example.com"

    with patch("app.services.notifications.settings", mock_settings):
        result = await send_email(sample_notification, ["user@example.com"])
    assert result is False
