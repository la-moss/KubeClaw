# TODO (Derived from Plan)

Status legend: `[done]`, `[in-progress]`, `[pending]`

## [done] T1 — Pin operating workflow

- Objective: Enforce plan-first / todo-first process for all changes.
- Files touched: `docs/operating-mode.md`
- Acceptance criteria: Workflow and hard constraints documented and explicit.
- Test to add/run: Manual review in PR checklist.

## [done] T2 — Research and decisions baseline

- Objective: Capture threat model, non-goals, invariants, and hard decisions.
- Files touched: `docs/research.md`, `docs/decisions.md`
- Acceptance criteria: Includes all required threats/invariants/defaults.
- Test to add/run: Manual doc lint/review.

## [done] T3 — Safety-layer implementation validation

- Objective: Ensure context/server/namespace/read-only/budget gates are enforced.
- Files touched: `agent/safety.py`, `tests/test_safety.py`
- Acceptance criteria: Wrong context/server and blocked verbs are refused.
- Test to add/run: `pytest tests/test_safety.py -q`

## [done] T4 — Redaction and output limits validation

- Objective: Ensure sensitive payloads are removed and outputs truncated safely.
- Files touched: `agent/redaction.py`, `tests/test_redaction.py`
- Acceptance criteria: Secret blocks/token/PEM redacted; truncation marker present.
- Test to add/run: `pytest tests/test_redaction.py -q`

## [done] T5 — Tool allowlist and runner enforcement

- Objective: Ensure only allowlisted read-only tools are executable.
- Files touched: `agent/tools.py`, `agent/runner.py`, `tests/test_runner.py`
- Acceptance criteria: No generic execution path; blocked verbs never run.
- Test to add/run: `pytest tests/test_runner.py -q`

## [done] T6 — Record/replay determinism

- Objective: Ensure snapshots are redacted, ordered, and replay-safe.
- Files touched: `agent/replay.py`, `tests/test_replay.py`
- Acceptance criteria: Replay mismatch errors clear; round-trip stable.
- Test to add/run: `pytest tests/test_replay.py -q`

## [done] T7 — Report contract enforcement

- Objective: Ensure 8-section report format with facts/inference separation.
- Files touched: `agent/report.py`, report tests
- Acceptance criteria: Markdown/plain format includes all required sections.
- Test to add/run: report section contract test.

## [done] T8 — CLI deterministic triage

- Objective: Keep v1 reasoning deterministic and read-only.
- Files touched: `agent/main.py`, `agent/runner.py`, `agent/tools.py`
- Acceptance criteria: Minimal class-based diagnostics and strict safety notes.
- Test to add/run: CLI smoke + scenario checks.

## [done] T9 — Incident labs and expected reasoning

- Objective: Keep 5 deterministic manifests and expected reasoning paths current.
- Files touched: `labs/*/manifest.yaml`, `labs/*/expected.md`
- Acceptance criteria: Reproducible in `demo`; expected reasoning matches observed evidence.
- Test to add/run: kind-backed scenario matrix in CI.

## [done] T10 — Continuous validation pipeline

- Objective: Run safety + unit + deterministic scenario checks on each PR.
- Files touched: `.github/workflows/ci.yml`, `scripts/ci_scenario_check.py`
- Acceptance criteria: CI fails on missing sections/safety signals/regressions.
- Test to add/run: local `pytest -q` + `python scripts/ci_scenario_check.py ...`

## [done] T11 — Adversarial hardening checks (Option A)

- Objective: Continuously validate refusal/scoping behavior under adversarial prompts.
- Files touched: `scripts/ci_adversarial_check.py`, `.github/workflows/ci.yml`, docs updates
- Acceptance criteria:
  - 8-section report still present
  - read-only + namespace safety signals present
  - no `--all-namespaces` drift
  - no execution-claim language for mutating actions
- Test to add/run:
  - `python scripts/ci_adversarial_check.py`
  - CI adversarial job on push/PR

## [done] T12 — Ambiguity phase hybrid scenarios (Option B)

- Objective: Validate correct hypothesis ranking when signals are mixed.
- Files touched: `labs/06-*`, `labs/07-*`, `.github/workflows/ci.yml`, docs updates
- Acceptance criteria:
  - hybrid scenarios reproducible in `demo`
  - reports keep 8 sections and identify primary cause with evidence
  - CI hybrid matrix passes with expected incident markers
- Test to add/run:
  - `python scripts/ci_scenario_check.py --lab 06-pending-quota --symptom \"Pending pod\" --expect \"pending\"`
  - `python scripts/ci_scenario_check.py --lab 07-oom-probe --symptom \"OOMKilled\" --expect \"oom\"`

## [in-progress] T13 — Scale & noise scenarios (Option C)

- Objective: Validate correct triage focus under high-noise namespace conditions.
- Files touched: `labs/10-*`, `labs/11-*`, `scripts/ci_scale_noise_check.py`, `.github/workflows/ci.yml`, docs updates
- Acceptance criteria:
  - noisy scenarios reproducible in `demo`
  - reports keep 8 sections and preserve primary diagnosis
  - observed facts remain bounded (`max-facts` guard)
  - no scope drift to `--all-namespaces`
- Test to add/run:
  - `python scripts/ci_scale_noise_check.py --lab 10-noisy-service-selector --symptom \"service unreachable\" --expect \"selector mismatch\" --max-facts 6`
  - `python scripts/ci_scale_noise_check.py --lab 11-noisy-pending-capacity --symptom \"Pending pod\" --expect \"Insufficient cpu\" --max-facts 6`

## Definition of Done (v1)

- All hard safety invariants are enforced in code and tests.
- Report contract is stable and validated in CI.
- All 5 incident classes pass deterministic scenario checks.
- Replay mode works offline with ordered call verification.
- No raw shell execution path exposed to model behavior.
