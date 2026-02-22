"""Record/replay harness for deterministic cluster-free testing."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .redaction import redact_text
from .tools import ToolResult


@dataclass(frozen=True)
class ReplayEvent:
    """Single recorded tool invocation result."""

    tool: str
    args: dict[str, Any]
    output: str


def generate_session_id() -> str:
    """Create stable timestamped session IDs for snapshots."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{random.randint(0, 0xFFFF):04x}"


class ReplayHarness:
    """Handle live, record, and replay execution modes."""

    def __init__(
        self,
        *,
        snapshots_root: Path,
        mode: str = "live",
        session_id: str | None = None,
    ) -> None:
        self.snapshots_root = snapshots_root
        self.mode = mode
        self.session_id = session_id or generate_session_id()
        self._replay_index = 0
        self._metadata: dict[str, Any] = {"session_id": self.session_id, "calls": []}

        if self.mode not in {"live", "record", "replay"}:
            raise ValueError("mode must be one of: live, record, replay")

        if self.mode == "record":
            self._session_dir.mkdir(parents=True, exist_ok=True)
            self._metadata.update(
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "record",
                }
            )
            self._write_metadata()
        elif self.mode == "replay":
            self._load_metadata()

    @property
    def _session_dir(self) -> Path:
        return self.snapshots_root / self.session_id

    @property
    def metadata_path(self) -> Path:
        return self._session_dir / "metadata.json"

    def _write_metadata(self) -> None:
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(
            json.dumps(self._metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _load_metadata(self) -> None:
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"replay metadata not found: {self.metadata_path}")
        self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        execute_live: Callable[[], ToolResult],
    ) -> ToolResult:
        """Execute tool in live/record/replay modes."""
        if self.mode == "replay":
            return self._replay(tool_name)

        result = execute_live()
        if self.mode == "record":
            self._record(tool_name, args, result)
        return result

    def _record(self, tool_name: str, args: dict[str, Any], result: ToolResult) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        index = len(self._metadata["calls"])
        filename = f"{index:03d}_{tool_name}_{stamp}.txt"
        snapshot_path = self._session_dir / filename

        payload = {
            "stdout": redact_text(result.stdout),
            "stderr": redact_text(result.stderr),
            "exit_code": result.exit_code,
        }
        snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        self._metadata["calls"].append(
            {
                "index": index,
                "tool": tool_name,
                "args": args,
                "snapshot": filename,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._write_metadata()

    def _replay(self, tool_name: str) -> ToolResult:
        calls = self._metadata.get("calls", [])
        if self._replay_index >= len(calls):
            raise RuntimeError("replay exhausted: no more recorded tool calls")

        item = calls[self._replay_index]
        self._replay_index += 1
        expected = item.get("tool")
        if expected != tool_name:
            raise RuntimeError(
                f"replay mismatch: expected tool '{expected}' but got '{tool_name}'"
            )

        snapshot_path = self._session_dir / item["snapshot"]
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return ToolResult(
            stdout=payload.get("stdout", ""),
            stderr=payload.get("stderr", ""),
            exit_code=int(payload.get("exit_code", 0)),
        )
