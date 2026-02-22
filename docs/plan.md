# Implementation Plan (v1)

## Repo Structure (Key Files)

- `agent/main.py` — CLI entrypoint and deterministic triage flow
- `agent/safety.py` — context/server/namespace/read-only gates + budgets
- `agent/redaction.py` — secret/token/PEM redaction + truncation
- `agent/tools.py` — read-only kubectl tool implementations (allowlist)
- `agent/runner.py` — `ToolCall` dispatch through allowlist only
- `agent/replay.py` — record/replay harness with metadata ordering checks
- `agent/report.py` — strict report section formatting (markdown/plain)
- `skills/*.md` — reasoning playbooks per incident class
- `labs/*/manifest.yaml` + `labs/*/expected.md` — deterministic test scenarios
- `tests/*.py` — unit/safety/replay/scenario checks
- `.github/workflows/ci.yml` — continuous validation pipeline

## Phase 1: Safety Layer

Design requirements:

- Context hard-check:
  - `kubectl config current-context == kind-kubeclaw`
  - current server URL must be local/kind (or explicit dev override)
- Namespace restrictions:
  - default `demo`
  - deny `kube-system` unless explicit allow
- Read-only enforcement:
  - deny verbs: `apply`, `patch`, `delete`, `edit`, `exec`, `port-forward`, `rollout`, `scale`, `drain`, `cordon`, `uncordon`, `taint`, `label`, `annotate`
- Tool allowlist:
  - no generic command strings
  - typed tool functions only
- Output and time budgets:
  - per-command timeout
  - max tool calls/run
  - max output chars with truncation marker

## Phase 2: Redaction and Output Controls

- Strip Secret YAML payload blocks: `data:` and `stringData:`
- Remove PEM blocks
- Redact bearer/JWT-like tokens and common secret fields
- Apply truncation marker (`[TRUNCATED]`) at output limit

## Phase 3: Controlled Execution (Runner + Tools)

- Execution path only via `ToolCall -> SafeRunner -> allowlisted tool`
- Each tool:
  - builds deterministic arg list
  - invokes kubectl with timeout/capture_output/no shell
  - runs safety assertions before execution
  - returns structured `stdout/stderr/exit_code` with redaction applied

## Phase 4: Snapshot Record + Replay

File layout:

- `snapshots/<session_id>/metadata.json`
- `snapshots/<session_id>/<index>_<tool>_<timestamp>.txt`

Metadata format includes ordered entries:

- tool name
- args
- snapshot filename
- timestamp

Replay behavior:

- Return stored output instead of live kubectl calls
- Raise clear mismatch error if requested tool sequence deviates

## Phase 5: Deterministic Triage Flow

Flow:

1. Objective
2. Gather observed facts via minimum read-only diagnostics
3. Interpretation from facts
4. Ranked hypotheses (1-3) with evidence
5. Single next best diagnostic
6. Proposed fix (text only)
7. Rollback plan (text only)
8. Safety notes

Scope:

- CrashLoopBackOff
- ImagePullBackOff
- Pending
- Service unreachable
- OOMKilled

## Phase 6: Test Strategy

Unit tests:

- mocked subprocess for safety gates and tool invocation
- redaction rule coverage
- replay ordering and persistence checks
- report section contract checks

Safety checklist tests:

- wrong context refused
- non-local server refused
- `kube-system` refused by default
- blocked verbs refused
- redaction and truncation enforced
- tool-call budget enforced

Continuous tests:

- unit suite on every push/PR
- kind-backed scenario matrix for 5 deterministic labs

## Phase 7: Adversarial Hardening (Option A)

Goal: intentionally stress policy boundaries and refusal behavior.

Test categories:

- Prompt injection attempts
- Namespace escalation requests
- Tool misuse requests
- Over-collection requests
- Conflicting-signal prompts

Acceptance criteria:

- Reports keep required 8 sections
- Safety notes remain explicit (`read-only`, scoped namespace)
- No `--all-namespaces` drift
- No privileged/mutating command suggestions presented as executed actions

Automation:

- Add `scripts/ci_adversarial_check.py` with deterministic adversarial prompt set
- Add CI job to run adversarial checks on each push/PR

## Phase 8: Ambiguity Phase (Option B)

Goal: validate reasoning depth when multiple plausible signals coexist.

Hybrid scenarios:

- Pod Pending + ResourceQuota present
- OOMKilled + probe failures
- (next) Service reachable + app 500
- (next) CrashLoop due to missing secret with secret existing elsewhere

Acceptance criteria:

- Correct primary hypothesis with explicit evidence ranking
- Conflicting signals are acknowledged, not collapsed into overconfident claims
- Report still conforms to 8-section contract and safety notes

Automation:

- Add `labs/06-*` and `labs/07-*` deterministic hybrid scenarios
- Add CI `hybrid-kind` matrix using scenario checks with expected class markers

## Phase 9: Scale & Noise Phase (Option C)

Goal: validate minimal-diagnostic behavior and hypothesis focus under noisy namespaces.

Scale/noise scenarios:

- Service selector mismatch with many unrelated healthy workloads
- Pending pod capacity failure with many unrelated healthy workloads

Acceptance criteria:

- Reports still satisfy the 8-section contract and safety notes
- Primary diagnosis remains correct despite noisy resources
- Observed facts remain bounded (no diagnostic sprawl)
- No scope drift (`--all-namespaces`) appears in outputs

Automation:

- Add `labs/10-*` and `labs/11-*` deterministic scale/noise scenarios
- Add `scripts/ci_scale_noise_check.py` with observed-facts budget validation
- Add CI `scale-noise-kind` matrix using scale/noise checks
