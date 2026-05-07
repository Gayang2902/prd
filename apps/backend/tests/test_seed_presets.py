"""Tests for seed presets."""

from app.services.seed_presets import BUILTIN_PRESETS


def test_builtin_presets_defined() -> None:
    assert len(BUILTIN_PRESETS) == 3
    names = {p["name"] for p in BUILTIN_PRESETS}
    assert "표준 보안 검수" in names
    assert "Quick Diff Scan" in names
    assert "PII 집중 스캔" in names


def test_builtin_presets_have_required_fields() -> None:
    for preset in BUILTIN_PRESETS:
        assert "name" in preset
        assert "prompt_template" in preset
        assert "ruleset" in preset
        assert "timeout_seconds" in preset
        assert preset["is_shared"] is True
