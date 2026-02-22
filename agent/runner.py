"""Safe tool-call runner with explicit allowlist dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .safety import register_tool_call, reset_tool_call_budget
from .tools import ToolResult, load_tool_allowlist


@dataclass(frozen=True)
class ToolCall:
    """Serializable representation of a single allowlisted tool call."""

    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ToolPlanStep:
    """Planned action with expected information gain rationale."""

    call: ToolCall
    expected_information_gain: str


class SafeRunner:
    """Execute only allowlisted read-only tools."""

    def __init__(self) -> None:
        self._allowlist = load_tool_allowlist()

    def reset(self) -> None:
        reset_tool_call_budget()

    def run_call(self, call: ToolCall) -> ToolResult:
        tool = self._allowlist.get(call.name)
        if tool is None:
            allowed = ", ".join(sorted(self._allowlist))
            raise ValueError(f"tool '{call.name}' is not allowlisted. allowed: {allowed}")
        register_tool_call()
        return tool(**call.args)


def build_triage_calls(ns: str, symptom: str) -> list[ToolCall]:
    """Back-compat shim returning calls from the richer plan."""
    return [step.call for step in build_triage_plan(ns, symptom)]


def build_triage_plan(ns: str, symptom: str) -> list[ToolPlanStep]:
    """Build deterministic tool plan with explicit information-gain justifications."""
    normalized = symptom.lower()
    plan: list[ToolPlanStep] = [
        ToolPlanStep(
            call=ToolCall("events_tail", {"ns": ns, "limit": 30}),
            expected_information_gain="Recent warning events reveal immediate failure reasons and timing.",
        )
    ]

    if "crash" in normalized:
        plan.append(
            ToolPlanStep(
                call=ToolCall(
                    "logs", {"ns": ns, "pod": "deployment/crashloop-demo", "tail": 120}
                ),
                expected_information_gain="Container logs expose startup exceptions and missing env/config signals.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall(
                    "logs", {"ns": ns, "pod": "deployment/crashloop-secret-demo", "tail": 120}
                ),
                expected_information_gain="Alternate crashloop deployment confirms secret-reference variants.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_deploy", {"ns": ns, "deploy": "crashloop-demo"}),
                expected_information_gain="Deployment describe provides restart/state transition evidence.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_deploy", {"ns": ns, "deploy": "crashloop-secret-demo"}),
                expected_information_gain="Cross-namespace secret and env wiring clues appear in deployment details.",
            )
        )
    elif "image" in normalized or "pull" in normalized:
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_deploy", {"ns": ns, "deploy": "imagepull-demo"}),
                expected_information_gain="Deployment events show image pull/auth errors with registry details.",
            )
        )
    elif "pending" in normalized:
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_pod", {"ns": ns, "pod": "pending-demo"}),
                expected_information_gain="Pod describe provides scheduler reason and resource shortage details.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_pod", {"ns": ns, "pod": "pending-quota-demo"}),
                expected_information_gain="Quota-related pending variant helps disambiguate scheduling vs quota limits.",
            )
        )
    elif "service unreachable" in normalized or "unreachable" in normalized:
        plan.append(
            ToolPlanStep(
                call=ToolCall("get_yaml", {"kind": "svc", "ns": ns, "name": "web-svc"}),
                expected_information_gain="Service selector and ports identify routing target configuration.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("get_yaml", {"kind": "ep", "ns": ns, "name": "web-svc"}),
                expected_information_gain="Endpoints object confirms whether backend addresses are populated.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("get_yaml", {"kind": "svc", "ns": ns, "name": "service-500-svc"}),
                expected_information_gain="Service 500 lab wiring distinguishes transport from app-level failures.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("get_yaml", {"kind": "ep", "ns": ns, "name": "service-500-svc"}),
                expected_information_gain="Endpoint status for 500 lab indicates if routing is functioning.",
            )
        )
    elif "oom" in normalized or "137" in normalized:
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_pod", {"ns": ns, "pod": "oom-demo"}),
                expected_information_gain="Pod state includes OOMKilled reason, exit code 137, and restart timing.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("describe_deploy", {"ns": ns, "deploy": "oom-probe-demo"}),
                expected_information_gain="Deployment probe status distinguishes probe failures from OOM side effects.",
            )
        )
        plan.append(
            ToolPlanStep(
                call=ToolCall("top_pod", {"ns": ns}),
                expected_information_gain="Runtime resource usage validates memory pressure hypothesis.",
            )
        )

    return plan
