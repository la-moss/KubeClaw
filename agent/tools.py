"""Strict tool implementations backed only by kubectl subprocess calls."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from .redaction import redact_text
from .safety import (
    assert_namespace_allowed,
    assert_read_only_cmd,
    assert_safe_context,
    load_safety_config,
)

ALLOWED_GET_YAML_KINDS = {
    "pod": "pod",
    "deploy": "deployment",
    "svc": "service",
    "ep": "endpoints",
    "cm": "configmap",
}

READ_ONLY_TOOL_NAMES = (
    "events_tail",
    "describe_pod",
    "describe_deploy",
    "logs",
    "get_yaml",
    "top_pod",
)


@dataclass(frozen=True)
class ToolResult:
    """Structured command result for safe runner/report plumbing."""

    stdout: str
    stderr: str
    exit_code: int


ToolFn = Callable[..., ToolResult]


def _run_kubectl(
    args: list[str], *, ns: str | None, allow_system: bool, allow_unsafe_cluster: bool
) -> ToolResult:
    """Execute kubectl safely with hard preflight checks."""
    cmd = ["kubectl", *args]
    assert_safe_context("kind-kubeclaw", allow_unsafe_cluster=allow_unsafe_cluster)
    if ns is not None:
        assert_namespace_allowed(ns, allow_system=allow_system)
    assert_read_only_cmd(cmd)

    config = load_safety_config()
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=config.command_timeout_seconds,
    )
    return ToolResult(
        stdout=redact_text(result.stdout or ""),
        stderr=redact_text(result.stderr or ""),
        exit_code=result.returncode,
    )


def events_tail(
    ns: str,
    *,
    limit: int = 30,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    result = _run_kubectl(
        [
            "get",
            "events",
            "-n",
            ns,
            "--sort-by=.metadata.creationTimestamp",
            "--field-selector=type!=Normal",
        ],
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )
    if result.exit_code != 0 or not result.stdout.strip():
        return result

    lines = result.stdout.splitlines()
    if len(lines) <= 1:
        return result

    # Preserve header and keep only the most recent rows.
    header = lines[0]
    body = lines[1:]
    trimmed = body[-max(1, limit) :]
    return ToolResult(
        stdout="\n".join([header, *trimmed]),
        stderr=result.stderr,
        exit_code=result.exit_code,
    )


def describe_pod(
    ns: str,
    pod: str,
    *,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    return _run_kubectl(
        ["describe", "pod", pod, "-n", ns],
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )


def describe_deploy(
    ns: str,
    deploy: str,
    *,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    return _run_kubectl(
        ["describe", "deployment", deploy, "-n", ns],
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )


def logs(
    ns: str,
    pod: str,
    *,
    container: str | None = None,
    previous: bool = False,
    tail: int = 200,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    args = ["logs", pod, "-n", ns, f"--tail={max(1, tail)}"]
    if container:
        args.extend(["-c", container])
    if previous:
        args.append("--previous")
    return _run_kubectl(
        args,
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )


def get_yaml(
    kind: str,
    ns: str,
    name: str,
    *,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    resource = ALLOWED_GET_YAML_KINDS.get(kind)
    if resource is None:
        allowed = ", ".join(sorted(ALLOWED_GET_YAML_KINDS))
        raise ValueError(f"unsupported kind '{kind}'. allowed: {allowed}")
    return _run_kubectl(
        ["get", resource, name, "-n", ns, "-o", "yaml"],
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )


def top_pod(
    ns: str,
    *,
    allow_system: bool = False,
    allow_unsafe_cluster: bool = False,
) -> ToolResult:
    result = _run_kubectl(
        ["top", "pod", "-n", ns],
        ns=ns,
        allow_system=allow_system,
        allow_unsafe_cluster=allow_unsafe_cluster,
    )
    combined = f"{result.stdout}\n{result.stderr}".lower()
    if "metrics api not available" in combined:
        return ToolResult(
            stdout="metrics-server is unavailable; skipping pod top output.",
            stderr=result.stderr,
            exit_code=0,
        )
    return result


def load_tool_allowlist() -> dict[str, ToolFn]:
    """Return explicit read-only tool allowlist."""
    return {
        "events_tail": events_tail,
        "describe_pod": describe_pod,
        "describe_deploy": describe_deploy,
        "logs": logs,
        "get_yaml": get_yaml,
        "top_pod": top_pod,
    }
