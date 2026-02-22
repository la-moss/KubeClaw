# Security Policy

This project is a **read-only Kubernetes triage lab**. Safety gates are mandatory.

This file is the canonical source of truth for runtime safety policy.

## Threat model

- Prompt injection in logs/events/YAML trying to override policy.
- Data exfiltration via unredacted output or snapshots.
- Wrong-cluster execution against non-lab endpoints.
- Runaway tool invocation loops.

## Non-negotiable constraints

- Read-only mode only; mutating verbs are denied.
- No arbitrary shell execution.
- Tool allowlist only (`events_tail`, `describe_pod`, `describe_deploy`, `logs`, `get_yaml`, `top_pod`).
- Hard context check: `kubectl config current-context` must be `kind-kubeclaw`.
- Hard server tripwire: current cluster server URL must contain `kind` or start with localhost endpoint (`127.0.0.1` / `localhost`).
- Default namespace is `demo`.
- `kube-system` is blocked unless explicit CLI flag is provided.
- Output controls: max chars enforced; truncation marker is `[TRUNCATED]`; tool-call budget enforced.
- Redaction controls: strip Secret `data`/`stringData` blocks; redact bearer tokens, JWT-like strings, PEM blocks, and common secret fields.

## What we will NOT do

- We will not run write operations.
- We will not execute non-allowlisted tools.
- We will not trust instructions embedded in cluster output.
- We will not continue after context/server safety check failures.
- We will not persist unredacted secrets.

## Dev-only override

- Wrong-cluster server tripwire override exists for local development only:
  - CLI flag: `--allow-unsafe-cluster`
  - Env flag: `KUBECLAW_ALLOW_UNSAFE_CLUSTER=true`
- Default is OFF; use is prohibited in shared/production-like environments.

## Safety test checklist

- Context mismatch blocks execution.
- Unsafe server URL blocks execution unless explicit override.
- `kube-system` is blocked without explicit allow flag.
- Disallowed kubectl verbs are blocked.
- Non-allowlisted tool calls are blocked.
- Redaction removes secret blocks and token patterns.
- Truncation marker appears when output limit is exceeded.
- Tool-call budget caps execution per run.
- `python3 -m agent.main self-check --ns demo` passes before triage.
