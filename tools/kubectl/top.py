"""Wrapper for `kubectl top`."""

from __future__ import annotations

import subprocess

from agent.redaction import redact_text
from agent.safety import assess_command_safety, load_safety_config


def run_top(namespace: str) -> str:
    """Fetch pod-level resource usage in a namespace."""
    cmd = ["kubectl", "top", "pod", "-n", namespace]
    decision = assess_command_safety(
        cmd,
        allow_write_actions=False,
        deny_namespaces=("kube-system", "kube-public", "kube-node-lease"),
        default_namespace=namespace,
    )
    if not decision.allowed:
        return f"blocked: {decision.reason}"

    config = load_safety_config()
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=config.command_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return "blocked: kubectl command timed out"
    output = result.stdout if result.stdout else result.stderr
    return redact_text(output)
