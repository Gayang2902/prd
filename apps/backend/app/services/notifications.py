"""Notification service with Slack webhook and Email stubs.

Trigger types:
1. analysis_completed — session finishes successfully
2. analysis_failed — session fails
3. budget_threshold — monthly cost exceeds threshold percentage
4. finding_critical — critical severity finding detected
"""

import enum
import uuid
from dataclasses import dataclass

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TriggerType(str, enum.Enum):
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    BUDGET_THRESHOLD = "budget_threshold"
    FINDING_CRITICAL = "finding_critical"


@dataclass
class Notification:
    trigger: TriggerType
    title: str
    body: str
    project_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None


async def send_slack(notification: Notification) -> bool:
    webhook_url = getattr(settings, "slack_webhook_url", None)
    if not webhook_url:
        logger.info("Slack webhook not configured, skipping", trigger=notification.trigger.value)
        return False

    try:
        import httpx

        payload = {
            "text": f"*[{notification.trigger.value}]* {notification.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{notification.title}*\n{notification.body}",
                    },
                }
            ],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        logger.info("Slack notification sent", trigger=notification.trigger.value)
        return True
    except Exception:
        logger.exception("Failed to send Slack notification")
        return False


async def send_email(notification: Notification, recipients: list[str]) -> bool:
    smtp_host = getattr(settings, "smtp_host", None)
    if not smtp_host:
        logger.info("SMTP not configured, skipping email", trigger=notification.trigger.value)
        return False

    logger.info(
        "Email notification would be sent",
        trigger=notification.trigger.value,
        recipients=recipients,
    )
    return False


async def notify(notification: Notification, email_recipients: list[str] | None = None) -> None:
    await send_slack(notification)
    if email_recipients:
        await send_email(notification, email_recipients)


async def notify_analysis_completed(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    finding_count: int,
    cost: str,
) -> None:
    await notify(
        Notification(
            trigger=TriggerType.ANALYSIS_COMPLETED,
            title="분석 완료",
            body=f"세션 `{str(session_id)[:8]}` 완료 — 발견 {finding_count}건, 비용 ${cost}",
            project_id=project_id,
            session_id=session_id,
        )
    )


async def notify_analysis_failed(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    reason: str,
) -> None:
    await notify(
        Notification(
            trigger=TriggerType.ANALYSIS_FAILED,
            title="분석 실패",
            body=f"세션 `{str(session_id)[:8]}` 실패: {reason}",
            project_id=project_id,
            session_id=session_id,
        )
    )


async def notify_budget_threshold(
    current_cost: str,
    budget: str,
    percentage: int,
) -> None:
    await notify(
        Notification(
            trigger=TriggerType.BUDGET_THRESHOLD,
            title=f"예산 {percentage}% 도달",
            body=f"현재 비용 ${current_cost} / 예산 ${budget} ({percentage}%)",
        )
    )


async def notify_critical_finding(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    finding_title: str,
) -> None:
    await notify(
        Notification(
            trigger=TriggerType.FINDING_CRITICAL,
            title="Critical 취약점 발견",
            body=f"세션 `{str(session_id)[:8]}`: {finding_title}",
            project_id=project_id,
            session_id=session_id,
        )
    )
