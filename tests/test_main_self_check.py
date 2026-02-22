"""Self-check command tests."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from agent.main import run_self_check
from agent.safety import SafetyViolation
from agent.skills_runtime import SkillLoadResult


def test_self_check_passes_with_safe_mocks(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.main.sync_skills",
        lambda: SkillLoadResult(
            loaded_count=3,
            copied_count=1,
            source_dir=Path("/tmp/src"),
            runtime_dir=Path("/tmp/dst"),
        ),
    )
    monkeypatch.setattr("agent.main.assert_safe_context", lambda *_a, **_k: None)
    monkeypatch.setattr("agent.main.assert_namespace_allowed", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "agent.main.assert_read_only_cmd",
        lambda *_a, **_k: (_ for _ in ()).throw(SafetyViolation("blocked")),
    )
    args = Namespace(ns="demo", allow_system=False, allow_unsafe_cluster=False)
    assert run_self_check(args) == 0


def test_self_check_fails_when_context_check_fails(monkeypatch) -> None:
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
        "agent.main.assert_safe_context",
        lambda *_a, **_k: (_ for _ in ()).throw(SafetyViolation("bad context")),
    )
    monkeypatch.setattr("agent.main.assert_namespace_allowed", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "agent.main.assert_read_only_cmd",
        lambda *_a, **_k: (_ for _ in ()).throw(SafetyViolation("blocked")),
    )
    args = Namespace(ns="demo", allow_system=False, allow_unsafe_cluster=False)
    assert run_self_check(args) == 1
