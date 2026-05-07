"""Tests for agent registry service."""

from unittest.mock import MagicMock, patch

from app.services.agent_registry import _registry, discover_agents, get_agent_metadata, get_registry
from securescope_schemas.agent_interface import BaseAgent


def setup_function() -> None:
    _registry.clear()


def test_discover_agents_no_entry_points() -> None:
    with patch("app.services.agent_registry.entry_points", return_value=[]):
        result = discover_agents()
    assert result == {}


def test_discover_agents_skips_non_agent() -> None:
    ep = MagicMock()
    ep.name = "bad"
    ep.load.return_value = "not a class"
    with patch("app.services.agent_registry.entry_points", return_value=[ep]):
        result = discover_agents()
    assert "bad" not in result


def test_discover_agents_registers_valid_agent() -> None:

    class FakeAgent(BaseAgent):
        async def prepare(self, ctx):
            pass

        async def analyze(self, ctx):
            yield  # type: ignore

        async def terminate(self):
            pass

        @classmethod
        def describe(cls):
            return MagicMock()

    ep = MagicMock()
    ep.name = "fake"
    ep.load.return_value = FakeAgent
    with patch("app.services.agent_registry.entry_points", return_value=[ep]):
        result = discover_agents()
    assert "fake" in result
    assert result["fake"] is FakeAgent


def test_get_registry_calls_discover_once() -> None:
    with patch("app.services.agent_registry.discover_agents") as mock_discover:
        mock_discover.return_value = {}
        get_registry()
        mock_discover.assert_called_once()


def test_get_registry_returns_cached() -> None:
    _registry["cached"] = MagicMock()
    result = get_registry()
    assert "cached" in result


def test_get_agent_metadata_empty() -> None:
    _registry.clear()
    with patch("app.services.agent_registry.entry_points", return_value=[]):
        metadata = get_agent_metadata()
    assert metadata == []
