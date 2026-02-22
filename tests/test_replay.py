"""Replay harness tests."""

from __future__ import annotations

import json
from pathlib import Path

from agent.replay import ReplayHarness
from agent.tools import ToolResult


def test_record_mode_writes_snapshots_and_metadata(tmp_path: Path) -> None:
    harness = ReplayHarness(snapshots_root=tmp_path, mode="record", session_id="sess-a")

    result = harness.execute(
        "events_tail",
        {"ns": "demo"},
        execute_live=lambda: ToolResult(stdout="token: abc", stderr="", exit_code=0),
    )
    assert result.exit_code == 0

    session_dir = tmp_path / "sess-a"
    metadata = json.loads((session_dir / "metadata.json").read_text(encoding="utf-8"))
    assert len(metadata["calls"]) == 1
    snap_file = metadata["calls"][0]["snapshot"]
    payload = json.loads((session_dir / snap_file).read_text(encoding="utf-8"))
    assert "abc" not in payload["stdout"]
    assert "[REDACTED]" in payload["stdout"]


def test_replay_mode_returns_recorded_outputs(tmp_path: Path) -> None:
    recorder = ReplayHarness(snapshots_root=tmp_path, mode="record", session_id="sess-b")
    recorder.execute(
        "events_tail",
        {"ns": "demo"},
        execute_live=lambda: ToolResult(stdout="ok", stderr="", exit_code=0),
    )

    replay = ReplayHarness(snapshots_root=tmp_path, mode="replay", session_id="sess-b")
    out = replay.execute(
        "events_tail",
        {"ns": "demo"},
        execute_live=lambda: ToolResult(stdout="should-not-run", stderr="", exit_code=1),
    )
    assert out.stdout == "ok"
    assert out.exit_code == 0
