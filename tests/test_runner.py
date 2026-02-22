"""Safe runner and tool wrapper tests."""

from __future__ import annotations

import subprocess

import pytest

from agent.runner import SafeRunner, ToolCall, build_triage_plan
from agent.tools import events_tail, top_pod


def test_runner_rejects_non_allowlisted_tool() -> None:
    runner = SafeRunner()
    with pytest.raises(ValueError, match="not allowlisted"):
        runner.run_call(ToolCall(name="shell", args={"cmd": "ls"}))


def test_events_tail_uses_subprocess_without_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.tools.assert_safe_context", lambda *_a, **_k: None)
    monkeypatch.setattr("agent.tools.assert_namespace_allowed", lambda *_a, **_k: None)
    monkeypatch.setattr("agent.tools.assert_read_only_cmd", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "agent.tools.load_safety_config",
        lambda: type("Cfg", (), {"command_timeout_seconds": 7})(),
    )

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "kubectl"
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 7
        assert kwargs.get("shell", False) is False
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = events_tail("demo", limit=10)
    assert result.exit_code == 0
    assert result.stdout == "ok"


def test_top_pod_returns_helpful_message_when_metrics_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.tools.assert_safe_context", lambda *_a, **_k: None)
    monkeypatch.setattr("agent.tools.assert_namespace_allowed", lambda *_a, **_k: None)
    monkeypatch.setattr("agent.tools.assert_read_only_cmd", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "agent.tools.load_safety_config",
        lambda: type("Cfg", (), {"command_timeout_seconds": 5})(),
    )

    def fake_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="error: Metrics API not available",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = top_pod("demo")
    assert result.exit_code == 0
    assert "metrics-server is unavailable" in result.stdout


def test_build_triage_plan_contains_info_gain_annotations() -> None:
    plan = build_triage_plan("demo", "service unreachable")
    assert plan
    assert all(step.expected_information_gain for step in plan)
