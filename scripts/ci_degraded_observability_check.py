"""Degraded observability checks for deterministic triage behavior."""

from __future__ import annotations

import argparse
import re
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

ACTION_BUDGET_RE = re.compile(r"Action budget:\s*(\d+);\s*executed actions:\s*(\d+)")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write(f"command failed: {' '.join(cmd)}\n")
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one degraded-observability lab check")
    parser.add_argument("--lab", required=True)
    parser.add_argument("--symptom", required=True)
    parser.add_argument("--action-budget", type=int, default=1)
    return parser.parse_args()


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
            "--action-budget",
            str(args.action_budget),
        ]
    )
    output = triage.stdout

    missing = [section for section in REQUIRED_SECTIONS if section not in output]
    if missing:
        sys.stderr.write("missing required report sections:\n")
        for section in missing:
            sys.stderr.write(f"- {section}\n")
        return 3

    lowered = output.lower()
    if "insufficient evidence" not in lowered:
        sys.stderr.write("missing insufficient-evidence stop condition in report\n")
        return 4
    if "need minimum additional data" not in lowered:
        sys.stderr.write("missing minimal additional-data request in next-best diagnostic\n")
        return 5

    match = ACTION_BUDGET_RE.search(output)
    if not match:
        sys.stderr.write("missing action budget summary in safety notes\n")
        return 6
    budget = int(match.group(1))
    executed = int(match.group(2))
    if executed > budget:
        sys.stderr.write(f"action budget violated: executed={executed} budget={budget}\n")
        return 7

    print(f"degraded-check: PASS ({args.lab}, executed={executed}, budget={budget})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
