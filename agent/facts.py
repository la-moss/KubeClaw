"""Golden fact extraction and deterministic incident classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


INCIDENT_TYPES = ("crashloop", "imagepull", "pending", "service_unreachable", "oom", "generic")

ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
AGE_TOKEN_RE = re.compile(r"(?<!\w)(\d+)([smhd])(?!\w)")

CRASHLOOP_PATTERNS = ("back-off", "crashloopbackoff", "database_url")
IMAGEPULL_PATTERNS = ("failed to pull image", "imagepull", "does-not-exist", "errimagepull")
PENDING_PATTERNS = ("failedscheduling", "insufficient cpu", "pending", "resourcequota")
SERVICE_PATTERNS = ("endpoints", "selector", "subsets: []", "service unreachable", "500")
OOM_PATTERNS = ("oomkilled", "exit code: 137", "readiness probe failed", "memory")


@dataclass(frozen=True)
class GoldenFact:
    source: str
    text: str
    timestamp: datetime | None
    stale: bool


@dataclass(frozen=True)
class FactBundle:
    facts: list[GoldenFact]
    excluded_stale_count: int
    tool_failures: int
    classification: str
    insufficient_evidence: bool


def _parse_timestamp(line: str, now: datetime) -> datetime | None:
    iso = ISO_TIMESTAMP_RE.search(line)
    if iso:
        try:
            return datetime.fromisoformat(iso.group(0).replace("Z", "+00:00"))
        except ValueError:
            return None

    age = AGE_TOKEN_RE.search(line.lower())
    if not age:
        return None

    value = int(age.group(1))
    unit = age.group(2)
    if unit == "s":
        return now - timedelta(seconds=value)
    if unit == "m":
        return now - timedelta(minutes=value)
    if unit == "h":
        return now - timedelta(hours=value)
    if unit == "d":
        return now - timedelta(days=value)
    return None


def _matches_any(line: str, patterns: tuple[str, ...]) -> bool:
    lowered = line.lower()
    return any(pattern in lowered for pattern in patterns)


def _incident_signal_counts(lines: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in INCIDENT_TYPES}
    for line in lines:
        lowered = line.lower()
        if _matches_any(lowered, CRASHLOOP_PATTERNS):
            counts["crashloop"] += 1
        if _matches_any(lowered, IMAGEPULL_PATTERNS):
            counts["imagepull"] += 1
        if _matches_any(lowered, PENDING_PATTERNS):
            counts["pending"] += 1
        if _matches_any(lowered, SERVICE_PATTERNS):
            counts["service_unreachable"] += 1
        if _matches_any(lowered, OOM_PATTERNS):
            counts["oom"] += 1
    return counts


def classify_from_facts(facts: list[GoldenFact], symptom: str) -> str:
    if facts:
        counts = _incident_signal_counts([fact.text for fact in facts])
        if counts["oom"] > 0:
            return "oom"
        ranked = sorted(
            ((k, v) for k, v in counts.items() if k != "generic"),
            key=lambda item: item[1],
            reverse=True,
        )
        if ranked and ranked[0][1] > 0:
            return ranked[0][0]

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


def _is_golden_line(line: str) -> bool:
    lowered = line.lower()
    all_patterns = (
        CRASHLOOP_PATTERNS
        + IMAGEPULL_PATTERNS
        + PENDING_PATTERNS
        + SERVICE_PATTERNS
        + OOM_PATTERNS
    )
    return any(pattern in lowered for pattern in all_patterns)


def extract_fact_bundle(
    *,
    raw_results: list[tuple[str, int, str]],
    symptom: str,
    now: datetime | None = None,
    stale_window_minutes: int = 30,
    include_stale_evidence: bool = False,
) -> FactBundle:
    """Extract compact, timestamp-aware golden facts from tool outputs."""
    current = now or datetime.now(timezone.utc)
    stale_cutoff = current - timedelta(minutes=max(1, stale_window_minutes))
    facts: list[GoldenFact] = []
    excluded_stale = 0
    tool_failures = 0

    for source, exit_code, body in raw_results:
        if exit_code != 0:
            tool_failures += 1

        lines = [line.strip() for line in body.splitlines() if line.strip()]
        selected = [line for line in lines if _is_golden_line(line)]
        if not selected and lines:
            selected = [lines[0]]

        for line in selected:
            stamp = _parse_timestamp(line, current)
            is_stale = bool(stamp and stamp < stale_cutoff)
            if is_stale and not include_stale_evidence:
                excluded_stale += 1
                continue
            facts.append(
                GoldenFact(
                    source=source,
                    text=line,
                    timestamp=stamp,
                    stale=is_stale,
                )
            )

    classification = classify_from_facts(facts, symptom)
    insufficient = (
        len(raw_results) < 2
        or len(facts) < 2
        or all("no output" in fact.text.lower() for fact in facts)
    )
    return FactBundle(
        facts=facts,
        excluded_stale_count=excluded_stale,
        tool_failures=tool_failures,
        classification=classification,
        insufficient_evidence=insufficient,
    )
