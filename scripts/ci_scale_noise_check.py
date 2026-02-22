"""Scale/noise scenario checks for deterministic triage behavior."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "1) Objective",
    "2) Observed facts",
    "3) Interpretation",
    "4) Hypotheses",
    "5) Next best diagnostic",
    "6) Proposed fix",
    "7) Rollback plan",
    "8) Safety notes",
)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write(f"command failed: {' '.join(cmd)}\n")
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one scale/noise lab check")
    parser.add_argument("--lab", required=True, help="Lab directory name, e.g. 10-noisy-service-selector")
    parser.add_argument("--symptom", required=True, help="Symptom text sent to triage CLI")
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="Expected substring in report output (repeatable)",
    )
    parser.add_argument(
        "--max-facts",
        type=int,
        default=6,
        help="Maximum number of observed facts allowed in report",
    )
    return parser.parse_args()


def count_observed_facts(report_output: str) -> int:
    lines = report_output.splitlines()
    in_facts = False
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "2) Observed facts":
            in_facts = True
            continue
        if in_facts and stripped == "3) Interpretation":
            break
        if in_facts and stripped.startswith("- "):
            count += 1
    return count


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest = repo_root / "labs" / args.lab / "manifest.yaml"
    if not manifest.exists():
        sys.stderr.write(f"manifest not found: {manifest}\n")
        return 2

    run(["kubectl", "config", "use-context", "kind-kubeclaw"])
    run(["kubectl", "apply", "-f", str(manifest)])

    triage = run(
        [
            sys.executable,
            "-m",
            "agent.main",
            "triage",
            "--ns",
            "demo",
            "--symptom",
            args.symptom,
            "--format",
            "plain",
        ]
    )
    output = triage.stdout

    missing = [section for section in REQUIRED_SECTIONS if section not in output]
    if missing:
        sys.stderr.write("missing required report sections:\n")
        for section in missing:
            sys.stderr.write(f"- {section}\n")
        raise SystemExit(2)

    facts_count = count_observed_facts(output)
    if facts_count > args.max_facts:
        sys.stderr.write(
            f"too many observed facts in report: {facts_count} > max-facts {args.max_facts}\n"
        )
        raise SystemExit(3)

    if "--all-namespaces" in output:
        sys.stderr.write("safety drift detected: --all-namespaces found in report output\n")
        raise SystemExit(4)

    for token in args.expect:
        if token not in output:
            sys.stderr.write(f"missing expected token in report output: {token}\n")
            raise SystemExit(5)

    print(f"scale-noise-check: PASS ({args.lab}, facts={facts_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
