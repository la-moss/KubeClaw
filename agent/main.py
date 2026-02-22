"""CLI entrypoint for deterministic triage mode."""

from __future__ import annotations

import argparse
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .facts import FactBundle, extract_fact_bundle
from .redaction import redact_text
from .replay import ReplayHarness
from .report import Hypothesis, TriageReport, format_markdown, format_plain_text
from .runner import SafeRunner, ToolCall, ToolPlanStep, build_triage_plan
from .safety import (
    SafetyViolation,
    assert_namespace_allowed,
    assert_read_only_cmd,
    assert_safe_context,
    reset_tool_call_budget,
)
from .skills_runtime import sync_skills
from .suggested_patch import render_suggested_fix
from .tools import ToolResult


FACT_KEYWORDS = (
    "database_url",
    "does-not-exist",
    "insufficient cpu",
    "oomkilled",
    "readiness probe failed",
    "selector",
    "endpoints",
    "resourcequota",
    "secret",
    "500",
    "exit code",
    "reason",
)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser with triage-only workflow."""
    parser = argparse.ArgumentParser(description="kubeclaw triage runner")
    sub = parser.add_subparsers(dest="command", required=True)
    triage = sub.add_parser("triage", help="Run deterministic read-only triage")
    triage.add_argument("--ns", default="demo", help="Target namespace")
    triage.add_argument("--symptom", required=True, help="Symptom description")
    triage.add_argument("--allow-system", action="store_true", help="Allow kube-system access")
    triage.add_argument(
        "--allow-unsafe-cluster",
        action="store_true",
        help="Dev-only override for server tripwire checks",
    )
    triage.add_argument("--replay", help="Replay from snapshots/<session_id>")
    triage.add_argument("--record", action="store_true", help="Record tool outputs for replay")
    triage.add_argument(
        "--format",
        choices=("markdown", "plain"),
        default="markdown",
        help="Output format",
    )
    triage.add_argument(
        "--include-stale-evidence",
        action="store_true",
        help="Include stale timestamped evidence in reasoning output",
    )
    triage.add_argument(
        "--stale-window-minutes",
        type=int,
        default=30,
        help="Ignore timestamped evidence older than this window unless overridden",
    )
    triage.add_argument(
        "--action-budget",
        type=int,
        default=6,
        help="Maximum tool calls per triage run",
    )
    check = sub.add_parser("self-check", help="Run safety and replay self-checks")
    check.add_argument("--ns", default="demo", help="Namespace to validate")
    check.add_argument("--allow-system", action="store_true", help="Allow kube-system namespace")
    check.add_argument(
        "--allow-unsafe-cluster",
        action="store_true",
        help="Dev-only override for server tripwire checks",
    )
    return parser


def _classify_symptom(symptom: str) -> str:
    lowered = symptom.lower()
    if "crash" in lowered:
        return "crashloop"
    if "image" in lowered or "pull" in lowered:
        return "imagepull"
    if "pending" in lowered:
        return "pending"
    if "unreachable" in lowered or "service" in lowered:
        return "service_unreachable"
    if "oom" in lowered or "137" in lowered:
        return "oom"
    return "generic"


def _first_fact_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "no output"
    lowered = [line.lower() for line in lines]
    for keyword in FACT_KEYWORDS:
        for idx, line in enumerate(lowered):
            if keyword in line:
                return lines[idx]
    return lines[0]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _hypothesis_confidence(
    bundle: FactBundle,
    *,
    is_primary: bool,
    contradiction_count: int,
) -> float:
    coverage = min(1.0, len(bundle.facts) / 6.0)
    score = 0.35 + (0.4 * coverage)
    if is_primary:
        score += 0.1
    score -= 0.08 * bundle.tool_failures
    score -= 0.1 * contradiction_count
    if bundle.insufficient_evidence:
        score -= 0.2
    return _clamp(score, 0.05, 0.95)


def _count_incident_contradictions(bundle: FactBundle, primary_incident: str) -> int:
    lowered = [fact.text.lower() for fact in bundle.facts]
    incident_markers = {
        "crashloop": ("crashloop", "back-off", "database_url"),
        "imagepull": ("imagepull", "failed to pull image", "errimagepull"),
        "pending": ("failedscheduling", "insufficient cpu", "resourcequota"),
        "service_unreachable": ("endpoints", "selector", "subsets: []"),
        "oom": ("oomkilled", "exit code: 137"),
    }
    contradictions = 0
    for incident, markers in incident_markers.items():
        if incident == primary_incident:
            continue
        if any(any(marker in line for marker in markers) for line in lowered):
            contradictions += 1
    return contradictions


def _format_observed_facts(bundle: FactBundle) -> list[str]:
    if not bundle.facts:
        return ["No tool output captured."]
    formatted: list[str] = []
    for fact in bundle.facts[:6]:
        stamp = fact.timestamp.isoformat() if fact.timestamp else "timestamp unavailable"
        formatted.append(f"{fact.source}: {fact.text} (evidence_time={stamp})")
    return formatted


def _build_next_action(incident: str, ns: str, insufficient: bool) -> str:
    if insufficient:
        return (
            f"Need minimum additional data: describe_pod --ns {ns} --pod <affected-pod>\n"
            f"Lookahead: If pod reason shows FailedScheduling -> run events_tail --ns {ns} --limit 30; "
            f"if pod reason shows CrashLoopBackOff/ImagePullBackOff -> run logs --ns {ns} --pod <affected-pod> --previous --tail 200."
        )
    mapping = {
        "crashloop": (
            f"logs --ns {ns} --pod deployment/crashloop-demo --previous --tail 200",
            f"If logs show missing env/secret -> inspect describe_deploy --ns {ns} --deploy crashloop-demo; "
            f"if logs show runtime exception -> inspect get_yaml --kind deploy --ns {ns} --name crashloop-demo.",
        ),
        "imagepull": (
            f"describe_deploy --ns {ns} --deploy imagepull-demo",
            f"If image tag/auth error appears -> verify image reference; if no pull error appears -> inspect events_tail --ns {ns} --limit 30.",
        ),
        "pending": (
            f"describe_pod --ns {ns} --pod pending-demo",
            f"If FailedScheduling mentions cpu -> reduce request; if quota-related -> inspect ResourceQuota usage.",
        ),
        "service_unreachable": (
            f"get_yaml --kind ep --ns {ns} --name web-svc",
            f"If endpoints empty -> compare selector/labels; if endpoints populated -> investigate app-level 500 path.",
        ),
        "oom": (
            f"describe_pod --ns {ns} --pod oom-demo",
            f"If OOMKilled/137 confirmed -> tune memory limits; if not, inspect probe failures and restart patterns.",
        ),
    }
    action, lookahead = mapping.get(
        incident,
        (
            f"events_tail --ns {ns} --limit 30",
            "If warning events are present -> follow dominant reason; if no warning events -> request targeted describe/logs for affected workload.",
        ),
    )
    return f"{action}\nLookahead: {lookahead}"


def _report_for(
    *,
    symptom: str,
    ns: str,
    bundle: FactBundle,
    action_budget: int,
    executed_actions: int,
) -> TriageReport:
    incident = bundle.classification
    contradiction_count = _count_incident_contradictions(bundle, incident)
    primary_conf = _hypothesis_confidence(
        bundle, is_primary=True, contradiction_count=contradiction_count
    )
    secondary_conf = _hypothesis_confidence(
        bundle, is_primary=False, contradiction_count=contradiction_count
    ) - 0.1
    tertiary_conf = _hypothesis_confidence(
        bundle, is_primary=False, contradiction_count=contradiction_count
    ) - 0.2

    hypotheses = [
        Hypothesis(
            rank=1,
            statement=f"Primary incident class is '{incident}'.",
            evidence=[fact.text for fact in bundle.facts[:2]] or ["No direct facts captured."],
            confidence=_clamp(primary_conf, 0.05, 0.99),
            what_would_change_my_mind=_build_next_action(incident, ns, True).splitlines()[0],
        ),
        Hypothesis(
            rank=2,
            statement="Configuration mismatch is a plausible alternative.",
            evidence=[fact.text for fact in bundle.facts[2:4]] or ["Workload metadata should be verified."],
            confidence=_clamp(secondary_conf, 0.05, 0.85),
            what_would_change_my_mind=f"get_yaml --kind deploy --ns {ns} --name <affected-deploy>",
        ),
        Hypothesis(
            rank=3,
            statement="Resource/runtime constraints may be contributing.",
            evidence=[fact.text for fact in bundle.facts[4:6]] or ["Requests/limits and restart timing should be checked."],
            confidence=_clamp(tertiary_conf, 0.05, 0.7),
            what_would_change_my_mind=f"top_pod --ns {ns}",
        ),
    ]

    if bundle.insufficient_evidence:
        interpretation = (
            "Insufficient evidence to reach a high-confidence diagnosis. "
            "Stop condition triggered to prevent low-value diagnostic sprawl."
        )
    else:
        interpretation = (
            f"Deterministic classifier selected '{incident}' from golden facts while "
            f"excluding stale evidence count={bundle.excluded_stale_count}."
        )
        if incident == "service_unreachable":
            interpretation += " Primary signal indicates selector mismatch and/or empty endpoints."
        elif incident == "pending":
            interpretation += " Primary signal indicates FailedScheduling and capacity pressure."
        elif incident == "imagepull":
            interpretation += " Primary signal indicates failed image pull/registry resolution."
        elif incident == "crashloop":
            interpretation += " Primary signal indicates CrashLoop/Back-off startup failures."
        elif incident == "oom":
            interpretation += " Primary signal indicates OOMKilled/exit 137."

    suggestion = render_suggested_fix(incident)
    proposed_fix = (
        f"{suggestion.patch_text}\n"
        f"{suggestion.blast_radius}"
        if not bundle.insufficient_evidence
        else "Insufficient evidence for safe change recommendation; gather minimum additional data first."
    )

    return TriageReport(
        objective=f"User requested triage for symptom: {symptom}",
        observed_facts=_format_observed_facts(bundle),
        interpretation=interpretation,
        hypotheses=hypotheses,
        next_best_diagnostic=_build_next_action(incident, ns, bundle.insufficient_evidence),
        proposed_fix=proposed_fix,
        rollback_plan=suggestion.rollback_steps,
        safety_notes=[
            "Read-only mode enforced; no mutating kubectl verbs executed.",
            f"Namespace scope: {ns}",
            f"Action budget: {action_budget}; executed actions: {executed_actions}",
            f"Stale evidence ignored by default; excluded count: {bundle.excluded_stale_count}",
            "Tool outputs may be truncated/redacted before persistence.",
        ],
    )


def run_triage(args: argparse.Namespace) -> int:
    """Execute deterministic triage flow and print report."""
    if args.replay and args.record:
        raise ValueError("choose either --record or --replay, not both")

    mode = "live"
    if args.record:
        mode = "record"
    if args.replay:
        mode = "replay"

    skill_result = sync_skills()
    print(f"skills loaded: {skill_result.loaded_count}")

    runner = SafeRunner()
    runner.reset()
    harness = ReplayHarness(
        snapshots_root=Path("snapshots"),
        mode=mode,
        session_id=args.replay,
    )

    plan = build_triage_plan(args.ns, args.symptom)
    raw_results: list[tuple[str, int, str]] = []
    executed_actions = 0
    for step in plan:
        if executed_actions >= max(1, args.action_budget):
            break
        if not step.expected_information_gain.strip():
            raise ValueError(f"missing expected information gain for tool '{step.call.name}'")

        merged = dict(step.call.args)
        merged["allow_system"] = bool(args.allow_system)
        merged["allow_unsafe_cluster"] = bool(args.allow_unsafe_cluster)
        effective_call = ToolCall(name=step.call.name, args=merged)

        result = harness.execute(
            step.call.name,
            merged,
            execute_live=lambda c=effective_call: runner.run_call(c),
        )
        body = redact_text(result.stdout.strip() or result.stderr.strip())
        raw_results.append((step.call.name, result.exit_code, body))
        executed_actions += 1

    bundle = extract_fact_bundle(
        raw_results=raw_results,
        symptom=args.symptom,
        stale_window_minutes=max(1, args.stale_window_minutes),
        include_stale_evidence=bool(args.include_stale_evidence),
    )
    report = _report_for(
        symptom=args.symptom,
        ns=args.ns,
        bundle=bundle,
        action_budget=max(1, args.action_budget),
        executed_actions=executed_actions,
    )
    output = format_markdown(report) if args.format == "markdown" else format_plain_text(report)
    print(output, end="")

    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ext = "md" if args.format == "markdown" else "txt"
    report_path = report_dir / f"triage-{stamp}.{ext}"
    report_path.write_text(output, encoding="utf-8")
    print(f"\nreport: {report_path}")
    if mode == "record":
        print(f"recorded_session: {harness.session_id}")
    return 0


def run_self_check(args: argparse.Namespace) -> int:
    """Run local safety and plumbing checks before triage."""
    skill_result = sync_skills()
    print(f"skills loaded: {skill_result.loaded_count}")

    checks: list[tuple[str, bool, str]] = []

    try:
        assert_safe_context(
            "kind-kubeclaw", allow_unsafe_cluster=bool(args.allow_unsafe_cluster)
        )
        checks.append(("safe_context", True, "context and server are safe"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("safe_context", False, str(exc)))

    try:
        assert_namespace_allowed(args.ns, allow_system=bool(args.allow_system))
        checks.append(("namespace_guard", True, f"namespace '{args.ns}' allowed"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("namespace_guard", False, str(exc)))

    try:
        assert_read_only_cmd(["kubectl", "delete", "pod", "x", "-n", "demo"])
        checks.append(("write_verb_block", False, "delete unexpectedly allowed"))
    except SafetyViolation:
        checks.append(("write_verb_block", True, "mutating verb blocked"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("write_verb_block", False, str(exc)))

    secret_sample = "kind: Secret\ndata:\n  token: abc\nstringData:\n  password: p4ss\n"
    redacted = redact_text(secret_sample)
    if "abc" in redacted or "p4ss" in redacted:
        checks.append(("redaction", False, "secret values still present"))
    else:
        checks.append(("redaction", True, "secret values removed"))

    try:
        with tempfile.TemporaryDirectory(prefix="kubeclaw-selfcheck-") as temp_dir:
            root = Path(temp_dir)
            recorder = ReplayHarness(snapshots_root=root, mode="record", session_id="selfcheck")
            recorder.execute(
                "events_tail",
                {"ns": "demo"},
                execute_live=lambda: ToolResult(stdout="ok", stderr="", exit_code=0),
            )
            replay = ReplayHarness(snapshots_root=root, mode="replay", session_id="selfcheck")
            out = replay.execute(
                "events_tail",
                {"ns": "demo"},
                execute_live=lambda: ToolResult(stdout="wrong", stderr="", exit_code=1),
            )
            if out.stdout == "ok" and out.exit_code == 0:
                checks.append(("record_replay", True, "record/replay round trip works"))
            else:
                checks.append(("record_replay", False, "unexpected replay result"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("record_replay", False, str(exc)))

    reset_tool_call_budget()
    failures = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        prefix = "PASS" if ok else "FAIL"
        print(f"[{prefix}] {name}: {detail}")
    return 1 if failures else 0


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "triage":
        return run_triage(args)
    if args.command == "self-check":
        return run_self_check(args)
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
