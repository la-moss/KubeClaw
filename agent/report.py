"""Strict triage report formatting helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hypothesis:
    """Ranked hypothesis with direct evidence bullets."""

    rank: int
    statement: str
    evidence: list[str]
    confidence: float
    what_would_change_my_mind: str


@dataclass(frozen=True)
class TriageReport:
    """Structured report model with strict sectioning."""

    objective: str
    observed_facts: list[str]
    interpretation: str
    hypotheses: list[Hypothesis]
    next_best_diagnostic: str
    proposed_fix: str
    rollback_plan: str
    safety_notes: list[str]


def _ordered_hypotheses(items: list[Hypothesis]) -> list[Hypothesis]:
    ordered = sorted(items, key=lambda h: h.rank)
    return ordered[:3]


def format_markdown(report: TriageReport) -> str:
    """Render terminal-friendly markdown without tables."""
    lines = [
        "# Triage Report",
        "",
        "## 1) Objective",
        report.objective,
        "",
        "## 2) Observed facts",
    ]
    for fact in report.observed_facts:
        lines.append(f"- {fact}")

    lines.extend(
        [
            "",
            "## 3) Interpretation",
            report.interpretation,
            "",
            "## 4) Hypotheses",
        ]
    )
    for hyp in _ordered_hypotheses(report.hypotheses):
        lines.append(f"{hyp.rank}. {hyp.statement}")
        lines.append(f"   - Confidence: {hyp.confidence:.2f}")
        lines.append(f"   - What would change my mind: {hyp.what_would_change_my_mind}")
        for ev in hyp.evidence:
            lines.append(f"   - Evidence: {ev}")

    lines.extend(
        [
            "",
            "## 5) Next best diagnostic",
            f"`{report.next_best_diagnostic}`",
            "",
            "## 6) Proposed fix",
            report.proposed_fix,
            "",
            "## 7) Rollback plan",
            report.rollback_plan,
            "",
            "## 8) Safety notes",
        ]
    )
    for note in report.safety_notes:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def format_plain_text(report: TriageReport) -> str:
    """Render Slack-friendly plain text output."""
    lines = [
        "Triage Report",
        "",
        "1) Objective",
        report.objective,
        "",
        "2) Observed facts",
    ]
    for fact in report.observed_facts:
        lines.append(f"- {fact}")

    lines.extend(
        [
            "",
            "3) Interpretation",
            report.interpretation,
            "",
            "4) Hypotheses",
        ]
    )
    for hyp in _ordered_hypotheses(report.hypotheses):
        lines.append(f"{hyp.rank}. {hyp.statement}")
        lines.append(f"   Confidence: {hyp.confidence:.2f}")
        lines.append(f"   What would change my mind: {hyp.what_would_change_my_mind}")
        for ev in hyp.evidence:
            lines.append(f"   Evidence: {ev}")

    lines.extend(
        [
            "",
            "5) Next best diagnostic",
            report.next_best_diagnostic,
            "",
            "6) Proposed fix",
            report.proposed_fix,
            "",
            "7) Rollback plan",
            report.rollback_plan,
            "",
            "8) Safety notes",
        ]
    )
    for note in report.safety_notes:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"
