"""Main triage flow tests for uncertainty and action budget behavior."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from agent.main import run_triage
from agent.runner import ToolCall, ToolPlanStep
from agent.skills_runtime import SkillLoadResult
from agent.tools import ToolResult


def _args(**overrides) -> Namespace:
    base = {
        "ns": "demo",
        "symptom": "service unreachable",
        "allow_system": False,
        "allow_unsafe_cluster": False,
        "replay": None,
        "record": False,
        "format": "plain",
        "include_stale_evidence": False,
        "stale_window_minutes": 30,
        "action_budget": 1,
    }
    base.update(overrides)
    return Namespace(**base)


def test_run_triage_stops_with_insufficient_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.main.sync_skills",
        lambda: SkillLoadResult(
            loaded_count=1,
            copied_count=0,
            source_dir=Path("/tmp/src"),
            runtime_dir=Path("/tmp/dst"),
        ),
    )
    monkeypatch.setattr(
        "agent.main.build_triage_plan",
        lambda _ns, _symptom: [
            ToolPlanStep(
                call=ToolCall("events_tail", {"ns": "demo", "limit": 30}),
                expected_information_gain="events",
            )
        ],
    )
    monkeypatch.setattr(
        "agent.main.SafeRunner.run_call",
        lambda _self, _call: ToolResult(stdout="", stderr="", exit_code=0),
    )

    captured: list[str] = []
    monkeypatch.setattr("builtins.print", lambda *a, **_k: captured.append(" ".join(str(x) for x in a)))
    code = run_triage(_args())
    assert code == 0
    joined = "\n".join(captured).lower()
    assert "insufficient evidence" in joined
    assert "need minimum additional data" in joined


def test_run_triage_respects_action_budget(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.main.sync_skills",
        lambda: SkillLoadResult(
            loaded_count=1,
            copied_count=0,
            source_dir=Path("/tmp/src"),
            runtime_dir=Path("/tmp/dst"),
        ),
    )
    monkeypatch.setattr(
        "agent.main.build_triage_plan",
        lambda _ns, _symptom: [
            ToolPlanStep(ToolCall("events_tail", {"ns": "demo", "limit": 30}), "events"),
            ToolPlanStep(ToolCall("describe_pod", {"ns": "demo", "pod": "x"}), "describe"),
            ToolPlanStep(ToolCall("logs", {"ns": "demo", "pod": "x"}), "logs"),
        ],
    )
    calls = {"count": 0}

    def fake_run_call(_self, _call):
        calls["count"] += 1
        return ToolResult(stdout="FailedScheduling Insufficient cpu", stderr="", exit_code=0)

    monkeypatch.setattr("agent.main.SafeRunner.run_call", fake_run_call)
    code = run_triage(_args(action_budget=2, symptom="Pending pod"))
    assert code == 0
    assert calls["count"] == 2
