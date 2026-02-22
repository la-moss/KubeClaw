"""Report rendering tests for confidence/uncertainty fields."""

from __future__ import annotations

from agent.report import Hypothesis, TriageReport, format_markdown, format_plain_text


def _sample_report() -> TriageReport:
    return TriageReport(
        objective="triage sample",
        observed_facts=["fact-a", "fact-b"],
        interpretation="sample interpretation",
        hypotheses=[
            Hypothesis(
                rank=1,
                statement="primary",
                evidence=["ev1"],
                confidence=0.73,
                what_would_change_my_mind="describe_pod --ns demo --pod x",
            )
        ],
        next_best_diagnostic="events_tail --ns demo --limit 30",
        proposed_fix="text-only patch",
        rollback_plan="rollback text",
        safety_notes=["read-only", "demo scope"],
    )


def test_markdown_includes_confidence_and_change_my_mind() -> None:
    output = format_markdown(_sample_report())
    assert "Confidence: 0.73" in output
    assert "What would change my mind: describe_pod --ns demo --pod x" in output


def test_plain_text_includes_confidence_and_change_my_mind() -> None:
    output = format_plain_text(_sample_report())
    assert "Confidence: 0.73" in output
    assert "What would change my mind: describe_pod --ns demo --pod x" in output
