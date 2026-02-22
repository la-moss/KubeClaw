"""Configuration loading for the lab agent."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Runtime settings pulled from environment variables."""

    kube_context: str
    kube_namespace: str
    allow_write_actions: bool
    deny_namespaces: tuple[str, ...]
    reports_dir: str
    snapshots_dir: str


def _to_bool(value: str, *, default: bool = False) -> bool:
    """Normalize common truthy values from environment variables."""
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AgentConfig:
    """Build an immutable config object for runtime consumers."""
    deny_raw = os.getenv(
        "DENY_NAMESPACES", "kube-system,kube-public,kube-node-lease"
    )
    deny_namespaces = tuple(x.strip() for x in deny_raw.split(",") if x.strip())
    return AgentConfig(
        kube_context=os.getenv("KUBE_CONTEXT", "kind-kubeclaw"),
        kube_namespace=os.getenv("KUBE_NAMESPACE", "demo"),
        allow_write_actions=_to_bool(os.getenv("ALLOW_WRITE_ACTIONS", "false")),
        deny_namespaces=deny_namespaces,
        reports_dir=os.getenv("REPORTS_DIR", "reports"),
        snapshots_dir=os.getenv("SNAPSHOTS_DIR", "snapshots"),
    )
