"""Hard safety gates for kubectl command execution."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


DISALLOWED_VERBS = {
    "apply",
    "patch",
    "delete",
    "edit",
    "exec",
    "port-forward",
    "scale",
    "drain",
    "cordon",
    "uncordon",
    "taint",
    "label",
    "annotate",
}


class SafetyViolation(RuntimeError):
    """Raised when an action violates hard safety gates."""


@dataclass(frozen=True)
class SafetyConfig:
    """Global safety knobs loaded from environment."""

    command_timeout_seconds: int
    max_tool_calls_per_run: int
    allow_unsafe_cluster: bool


@dataclass(frozen=True)
class SafetyDecision:
    """Decision object returned by command safety checks."""

    allowed: bool
    reason: str


_tool_calls_in_run = 0


def _read_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _to_bool(value: str, *, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_safety_config() -> SafetyConfig:
    """Load command timeout, tool-call budget, and dev-only override."""
    return SafetyConfig(
        command_timeout_seconds=_read_int("KUBECLAW_CMD_TIMEOUT_SECONDS", 10),
        max_tool_calls_per_run=_read_int("KUBECLAW_MAX_TOOL_CALLS", 10),
        allow_unsafe_cluster=_to_bool(
            os.getenv("KUBECLAW_ALLOW_UNSAFE_CLUSTER", "false")
        ),
    )


def reset_tool_call_budget() -> None:
    """Reset per-run tool usage counter."""
    global _tool_calls_in_run
    _tool_calls_in_run = 0


def register_tool_call() -> None:
    """Track tool calls and enforce configurable per-run max."""
    global _tool_calls_in_run
    config = load_safety_config()
    if _tool_calls_in_run >= config.max_tool_calls_per_run:
        raise SafetyViolation(
            "tool call limit exceeded: "
            f"max {config.max_tool_calls_per_run} calls per run"
        )
    _tool_calls_in_run += 1


def _run_kubectl_config(args: list[str]) -> str:
    config = load_safety_config()
    try:
        result = subprocess.run(
            ["kubectl", "config", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=config.command_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SafetyViolation(
            "kubectl config check timed out; refusing to run commands"
        ) from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        raise SafetyViolation(f"failed to read kube config: {detail}")

    output = result.stdout.strip()
    if not output:
        raise SafetyViolation("kubectl config returned empty output")
    return output


def get_current_kube_context() -> str:
    """Read current kubectl context with enforced timeout."""
    return _run_kubectl_config(["current-context"])


def get_current_cluster_server() -> str:
    """Read current cluster API server URL from kubeconfig."""
    return _run_kubectl_config(["view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}"])


def _server_looks_local_or_kind(server: str) -> bool:
    lowered = server.lower()
    if "kind" in lowered:
        return True
    localhost_prefixes = (
        "https://127.0.0.1",
        "http://127.0.0.1",
        "https://localhost",
        "http://localhost",
    )
    return lowered.startswith(localhost_prefixes)


def assert_safe_context(
    allowed_context: str = "kind-kubeclaw", *, allow_unsafe_cluster: bool = False
) -> None:
    """Require safe context and cluster server before command execution."""
    current = get_current_kube_context()
    if current != allowed_context:
        raise SafetyViolation(
            f"unsafe cluster context '{current}'; expected '{allowed_context}'"
        )

    server = get_current_cluster_server()
    config = load_safety_config()
    override = allow_unsafe_cluster or config.allow_unsafe_cluster
    if not _server_looks_local_or_kind(server) and not override:
        raise SafetyViolation(
            "unsafe cluster server URL "
            f"'{server}'. Expected a local/kind endpoint. "
            "Set --allow-unsafe-cluster (dev only) to override."
        )


def assert_namespace_allowed(ns: str, allow_system: bool) -> None:
    """Block protected namespaces unless explicitly allowed."""
    namespace = ns.strip()
    if not namespace:
        raise SafetyViolation("namespace is required")
    if namespace == "kube-system" and not allow_system:
        raise SafetyViolation(
            "namespace 'kube-system' is blocked unless allow_system=True"
        )


def _first_non_flag_token(tokens: list[str], *, start: int = 0) -> tuple[int, str] | None:
    for idx in range(start, len(tokens)):
        token = tokens[idx]
        if not token.startswith("-"):
            return idx, token
    return None


def assert_read_only_cmd(cmd: list[str]) -> None:
    """Reject mutating or privileged kubectl command forms."""
    if not cmd:
        raise SafetyViolation("command is empty")
    if cmd[0] != "kubectl":
        raise SafetyViolation("only kubectl commands are allowed")

    parsed = _first_non_flag_token(cmd, start=1)
    if parsed is None:
        raise SafetyViolation("kubectl command is missing a verb")

    verb_index, verb = parsed
    lowered = verb.lower()
    if lowered in DISALLOWED_VERBS:
        raise SafetyViolation(f"disallowed kubectl verb in read-only mode: '{lowered}'")

    if lowered == "rollout":
        next_token = _first_non_flag_token(cmd, start=verb_index + 1)
        if next_token and next_token[1].lower() == "restart":
            raise SafetyViolation(
                "disallowed kubectl operation in read-only mode: 'rollout restart'"
            )


WRITE_KEYWORDS = {"apply", "create", "delete", "edit", "patch", "replace", "scale", "rollout"}


def is_write_command(command: list[str]) -> bool:
    """Detect potentially mutating kubectl subcommands."""
    return any(token in WRITE_KEYWORDS for token in command)


def namespace_from_command(command: list[str], default_namespace: str) -> str:
    """Resolve namespace from flags, falling back to default."""
    for i, token in enumerate(command):
        if token in {"-n", "--namespace"} and i + 1 < len(command):
            return command[i + 1]
        if token.startswith("--namespace="):
            return token.split("=", 1)[1]
    return default_namespace


def assess_command_safety(
    command: list[str],
    *,
    allow_write_actions: bool,
    deny_namespaces: tuple[str, ...],
    default_namespace: str,
) -> SafetyDecision:
    """Apply hard policy gates before invoking kubectl."""
    try:
        register_tool_call()
        assert_safe_context("kind-kubeclaw")
        assert_read_only_cmd(command)
        ns = namespace_from_command(command, default_namespace)
        assert_namespace_allowed(ns, allow_system=False)
        if ns in deny_namespaces:
            raise SafetyViolation(f"namespace '{ns}' is denied by policy")
        if is_write_command(command) and not allow_write_actions:
            raise SafetyViolation("write actions are disabled")
    except SafetyViolation as exc:
        return SafetyDecision(False, str(exc))
    return SafetyDecision(True, "allowed")
