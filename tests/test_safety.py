"""Safety policy unit tests."""

from __future__ import annotations

import subprocess

import pytest

from agent.safety import (
    SafetyViolation,
    assert_namespace_allowed,
    assert_read_only_cmd,
    assert_safe_context,
    assess_command_safety,
    get_current_cluster_server,
    get_current_kube_context,
    namespace_from_command,
    reset_tool_call_budget,
)


def test_namespace_flag_override() -> None:
    cmd = ["kubectl", "get", "pods", "--namespace=lab"]
    assert namespace_from_command(cmd, "default") == "lab"


def test_get_current_kube_context_returns_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KUBECLAW_CMD_TIMEOUT_SECONDS", "3")

    def fake_run(*_args, **kwargs):
        assert kwargs["timeout"] == 3
        return subprocess.CompletedProcess(
            args=["kubectl", "config", "current-context"],
            returncode=0,
            stdout="kind-kubeclaw\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert get_current_kube_context() == "kind-kubeclaw"


def test_assert_safe_context_blocks_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.safety.get_current_kube_context", lambda: "minikube")
    monkeypatch.setattr(
        "agent.safety.get_current_cluster_server",
        lambda: "https://127.0.0.1:6443",
    )
    with pytest.raises(SafetyViolation, match="unsafe cluster context"):
        assert_safe_context("kind-kubeclaw")


def test_get_current_cluster_server_returns_server(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["kubectl", "config", "view"],
            returncode=0,
            stdout="https://127.0.0.1:6443",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert get_current_cluster_server() == "https://127.0.0.1:6443"


def test_assert_safe_context_blocks_unsafe_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.safety.get_current_kube_context", lambda: "kind-kubeclaw")
    monkeypatch.setattr(
        "agent.safety.get_current_cluster_server",
        lambda: "https://prod.company.internal:6443",
    )
    with pytest.raises(SafetyViolation, match="unsafe cluster server URL"):
        assert_safe_context("kind-kubeclaw")


def test_assert_safe_context_allows_unsafe_server_with_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.safety.get_current_kube_context", lambda: "kind-kubeclaw")
    monkeypatch.setattr(
        "agent.safety.get_current_cluster_server",
        lambda: "https://prod.company.internal:6443",
    )
    assert_safe_context("kind-kubeclaw", allow_unsafe_cluster=True)


def test_namespace_blocks_kube_system_without_override() -> None:
    with pytest.raises(SafetyViolation, match="kube-system"):
        assert_namespace_allowed("kube-system", allow_system=False)


def test_namespace_allows_kube_system_with_override() -> None:
    assert_namespace_allowed("kube-system", allow_system=True)


@pytest.mark.parametrize(
    "cmd",
    [
        ["kubectl", "apply", "-f", "manifest.yaml"],
        ["kubectl", "patch", "pod", "x", "-p", "{}"],
        ["kubectl", "delete", "pod", "x"],
        ["kubectl", "edit", "deploy", "x"],
        ["kubectl", "exec", "pod/x", "--", "sh"],
        ["kubectl", "port-forward", "pod/x", "8080:80"],
        ["kubectl", "scale", "deploy", "x", "--replicas=2"],
        ["kubectl", "drain", "node/x"],
        ["kubectl", "cordon", "node/x"],
        ["kubectl", "uncordon", "node/x"],
        ["kubectl", "taint", "nodes", "x", "a=b:NoSchedule"],
        ["kubectl", "label", "pod", "x", "a=b"],
        ["kubectl", "annotate", "pod", "x", "a=b"],
        ["kubectl", "rollout", "restart", "deploy/x"],
    ],
)
def test_assert_read_only_cmd_blocks_disallowed_verbs(cmd: list[str]) -> None:
    with pytest.raises(SafetyViolation):
        assert_read_only_cmd(cmd)


def test_assess_command_safety_allows_read_only_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.safety.assert_safe_context", lambda *_args, **_kwargs: None)
    reset_tool_call_budget()
    decision = assess_command_safety(
        ["kubectl", "get", "pods", "-n", "default"],
        allow_write_actions=False,
        deny_namespaces=(),
        default_namespace="default",
    )
    assert decision.allowed


def test_assess_command_safety_enforces_tool_call_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KUBECLAW_MAX_TOOL_CALLS", "1")
    monkeypatch.setattr("agent.safety.assert_safe_context", lambda *_args, **_kwargs: None)
    reset_tool_call_budget()

    first = assess_command_safety(
        ["kubectl", "get", "pods", "-n", "default"],
        allow_write_actions=False,
        deny_namespaces=(),
        default_namespace="default",
    )
    second = assess_command_safety(
        ["kubectl", "get", "pods", "-n", "default"],
        allow_write_actions=False,
        deny_namespaces=(),
        default_namespace="default",
    )
    assert first.allowed
    assert not second.allowed
    assert "tool call limit exceeded" in second.reason


def test_assess_command_safety_blocks_kube_system_without_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.safety.assert_safe_context", lambda *_args, **_kwargs: None)
    reset_tool_call_budget()
    decision = assess_command_safety(
        ["kubectl", "get", "pods", "-n", "kube-system"],
        allow_write_actions=False,
        deny_namespaces=(),
        default_namespace="default",
    )
    assert not decision.allowed
    assert "kube-system" in decision.reason
