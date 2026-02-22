"""Golden fact extraction and deterministic classifier tests."""

from __future__ import annotations

from datetime import datetime, timezone

from agent.facts import extract_fact_bundle


def test_extract_fact_bundle_filters_stale_evidence() -> None:
    now = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
    bundle = extract_fact_bundle(
        raw_results=[
            ("events_tail", 0, "Warning  FailedScheduling  2h  default-scheduler  0/1 nodes are available: Insufficient cpu.")
        ],
        symptom="Pending pod",
        now=now,
        stale_window_minutes=30,
        include_stale_evidence=False,
    )
    assert bundle.excluded_stale_count == 1
    assert bundle.insufficient_evidence is True


def test_classifier_prefers_fact_signals_over_symptom_text() -> None:
    bundle = extract_fact_bundle(
        raw_results=[
            ("describe_pod", 0, "Last State: Terminated\nReason: OOMKilled\nExit Code: 137")
        ],
        symptom="service unreachable",
    )
    assert bundle.classification == "oom"
