# KubeClaw (built on OpenClaw) - Still a WIP

**A safety-first, read-only Kubernetes incident triage agent for local clusters.**

KubeClaw is not an autonomous operator.  
It is not a self-healing system.  
It does not apply changes.

It is a controlled reasoning engine designed to:

- Diagnose common Kubernetes failures
- Propose safe remediation steps
- Generate structured triage reports
- Operate under strict guardrails
- Refuse dangerous operations
- Be replayable and testable offline

This project exists to explore **cognitive automation safely**.

## Project objective

Build a **deterministic, read-only Kubernetes triage agent** that:

1. Operates only against a local lab cluster (`kind-kubeclaw`)
2. Uses a strict tool allowlist
3. Separates reasoning from execution
4. Redacts sensitive output
5. Enforces context hard-checks
6. Can replay incidents offline from snapshots
7. Produces structured incident reports

## Core philosophy

Most Kubernetes automation targets execution (`apply`, deploy, sync loops).  
KubeClaw targets the reasoning layer:

- What failed?
- Why?
- What evidence supports that?
- What is the minimal safe fix?
- What is the rollback?

Execution is easy. Diagnosis is the hard part.

## Security-first architecture

### 1) Read-only mode (non-negotiable)

The agent blocks mutating verbs, including:
`apply`, `patch`, `delete`, `scale`, `rollout restart`, `exec`, `port-forward`, `drain`, `cordon`, `uncordon`, `taint`, `label`, `annotate`.

All remediation is text-only.

### 2) Strict tool allowlist

Allowed tools:

- `events_tail(ns)`
- `describe_pod(ns, pod)`
- `describe_deploy(ns, deploy)`
- `logs(ns, pod, container=None, previous=False, tail=200)`
- `get_yaml(kind, ns, name)`
- `top_pod(ns)` (optional)

No arbitrary shell and no generic command executor.

### 3) Context hard-check + wrong-cluster tripwire

Before any kubectl call:

- context must equal `kind-kubeclaw`
- cluster server must look local (`kind` in URL or localhost/127.0.0.1 endpoint)

Refuse execution otherwise.

### 4) Namespace scoping

- Default namespace: `demo`
- `kube-system` blocked unless explicitly allowed
- No cross-namespace scanning by default

### 5) Output redaction and limits

- Remove Secret `data:` / `stringData:` blocks
- Redact bearer tokens, JWT-like strings, PEM blocks
- Truncate oversized outputs with `[TRUNCATED]`
- Keep log tails bounded
- Snapshot files store redacted output only

### 6) Snapshot replay

Triage runs can record and replay:

- Record tool outputs to `snapshots/<session_id>/...`
- Replay offline without cluster access

This enables deterministic testing and safer debugging.

## Source of truth

- Security policy source of truth: `SECURITY.md`
- Engineering workflow source of truth: `docs/operating-mode.md`
- Report/output contract source of truth: `skills/99_output_format.md`

## Incident scope (v1)

KubeClaw handles five deterministic classes:

1. CrashLoopBackOff
2. ImagePullBackOff
3. Pending pods
4. Service unreachable
5. OOMKilled

Out-of-scope incidents are reported with limited interpretation.

## Output contract

Every report uses the same sections:

1. Objective
2. Observed facts
3. Interpretation
4. Hypotheses (ranked)
5. Next best diagnostic (single)
6. Proposed fix (text-only)
7. Rollback plan
8. Safety notes

Facts are separated from inference.

## One-command bootstrap

Run:

- `bash scripts/bootstrap.sh`

Bootstrap does:

- create `.venv`
- install dependencies
- verify `kubectl` and `kind`
- ensure `kind-kubeclaw` cluster/context
- ensure namespace `demo`
- optionally install metrics-server (`INSTALL_METRICS_SERVER=true`)
- run `python3 -m agent.main self-check --ns demo`

## Skills workspace model

- Canonical source: `./skills/*`
- Runtime workspace: `~/.kubeclaw/skills/*` (or `KUBECLAW_RUNTIME_SKILLS_DIR`)
- Startup sync validates checksums/mtimes and prints `skills loaded: N`

## CLI usage

- Self-check: `python3 -m agent.main self-check --ns demo`
- Triage: `python3 -m agent.main triage --ns demo --symptom "service unreachable"`

## Secret handling (non-negotiable)

- Never commit secrets (`.env`, kubeconfig files, tokens, API keys)
- Keep `.env` local-only and git-ignored
- Never store raw credentials in snapshots/reports/tests
