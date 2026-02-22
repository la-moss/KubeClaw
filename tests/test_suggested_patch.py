"""Safe suggested patch rendering tests."""

from __future__ import annotations

from agent.suggested_patch import render_suggested_fix


def test_service_selector_patch_is_text_only_and_contains_validation() -> None:
    suggestion = render_suggested_fix("service_unreachable")
    assert "Suggested YAML patch (text only" in suggestion.patch_text
    assert "selector" in suggestion.patch_text
    assert "kubectl get ep web-svc -n demo -o yaml" in suggestion.patch_text


def test_unknown_incident_returns_no_change_patch() -> None:
    suggestion = render_suggested_fix("generic")
    assert "Insufficient evidence" in suggestion.patch_text
    assert "No rollback required" in suggestion.rollback_steps
