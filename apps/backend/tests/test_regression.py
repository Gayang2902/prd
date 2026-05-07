"""Tests for regression matching algorithm."""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.finding import RegressionStatus


def _make_finding(session_id: uuid.UUID, fingerprint: str):
    f = MagicMock()
    f.id = uuid.uuid4()
    f.session_id = session_id
    f.fingerprint = fingerprint
    f.regression_status = RegressionStatus.NEW
    return f


def _make_session(project_id: uuid.UUID):
    s = MagicMock()
    s.id = uuid.uuid4()
    s.project_id = project_id
    s.state = "completed"
    return s


def test_no_prev_session_all_new() -> None:
    """When no prior session exists, all findings should be NEW."""
    import asyncio
    from app.services.regression import compute_regression_labels

    project_id = uuid.uuid4()
    session_id = uuid.uuid4()

    current_findings = [
        _make_finding(session_id, "fp1"),
        _make_finding(session_id, "fp2"),
        _make_finding(session_id, "fp3"),
    ]

    db = AsyncMock()
    # First query: current findings
    result1 = MagicMock()
    result1.scalars.return_value.all.return_value = current_findings
    # Second query: previous session (None)
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[result1, result2])
    db.flush = AsyncMock()

    counts = asyncio.run(compute_regression_labels(db, session_id, project_id))

    assert counts["new"] == 3
    assert counts["recurring"] == 0
    assert counts["resolved"] == 0


def test_with_prev_session_classifies_correctly() -> None:
    """Findings present in both sessions are RECURRING, only-new are NEW, only-old are RESOLVED."""
    import asyncio
    from app.services.regression import compute_regression_labels

    project_id = uuid.uuid4()
    session_id = uuid.uuid4()
    prev_session = _make_session(project_id)

    # fp1: in both (RECURRING), fp2: only current (NEW), fp3: only previous (RESOLVED)
    current_findings = [
        _make_finding(session_id, "fp1"),
        _make_finding(session_id, "fp2"),
    ]
    prev_findings = [
        _make_finding(prev_session.id, "fp1"),
        _make_finding(prev_session.id, "fp3"),
    ]

    db = AsyncMock()
    result1 = MagicMock()
    result1.scalars.return_value.all.return_value = current_findings
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = prev_session
    result3 = MagicMock()
    result3.scalars.return_value.all.return_value = prev_findings

    db.execute = AsyncMock(side_effect=[result1, result2, result3])
    db.flush = AsyncMock()

    counts = asyncio.run(compute_regression_labels(db, session_id, project_id))

    assert counts["new"] == 1
    assert counts["recurring"] == 1
    assert counts["resolved"] == 1

    assert current_findings[0].regression_status == RegressionStatus.RECURRING
    assert current_findings[1].regression_status == RegressionStatus.NEW
    assert prev_findings[1].regression_status == RegressionStatus.RESOLVED
