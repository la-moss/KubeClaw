# Research: KubeClaw (Lab Edition)

## Goal

KubeClaw (Lab Edition) is a deterministic, read-only Kubernetes incident triage agent for local `kind` clusters. It gathers evidence with tightly constrained diagnostics, separates facts from inference, and outputs structured triage reports with replayable, redacted snapshots.

## Threat Model

- Prompt injection from untrusted logs/events/YAML output
- Wrong-cluster execution against non-lab or production contexts
- Data leakage through unredacted logs, reports, or snapshots
- Runaway tool calls causing uncontrolled output or unsafe behavior

## Non-Goals

- No auto-remediation or write execution
- No Slack/chat automation for v1 scope
- No production cluster targeting
- No arbitrary kubectl command execution

## Key Architectural Principle

Reasoning and execution are separated: reasoning decides *what to inspect*, while execution is constrained to a fixed read-only tool interface with policy enforcement.

## Interfaces

- CLI only for v1 (`python -m agent.main ...`)

## Environments

- Local `kind` cluster only (`kind-kubeclaw`)

## Required Safety Invariants

- Context must be `kind-kubeclaw`
- Cluster server URL must be local/kind unless explicit dev override
- Namespace defaults to `demo`
- `kube-system` denied unless explicit allow flag
- Read-only verb enforcement (deny mutating/privileged kubectl verbs)
- Tool allowlist only (no arbitrary command strings)
- Output redaction before persistence
- Output size/time/tool-call budgets enforced
- Record/replay parity with deterministic ordering checks

## Open Questions

- Should v1 permit scoped cross-namespace diagnostics behind explicit flags?
- Should replay metadata include command timing and truncation markers explicitly?
- Should CI fail on report wording drift or only structural/safety drift?

## Recommended Defaults

- `KUBE_CONTEXT=kind-kubeclaw`
- `KUBE_NAMESPACE=demo`
- `KUBECLAW_CMD_TIMEOUT_SECONDS=10`
- `KUBECLAW_MAX_TOOL_CALLS=10`
- `KUBECLAW_ALLOW_UNSAFE_CLUSTER=false`
