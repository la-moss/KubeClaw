# Decisions Log

## D-001: Read-only by design

- Decision: Block all mutating and privileged kubectl verbs.
- Why: Prevent accidental or malicious state change during triage.

## D-002: Context hard-check + server tripwire

- Decision: Require context `kind-kubeclaw` and local/kind API server URL.
- Why: Prevent wrong-cluster execution and production blast radius.

## D-003: Tool allowlist only

- Decision: Expose fixed read-only tool functions, no generic raw command interface.
- Why: Execution boundary is the primary safety control.

## D-004: Redact before persistence

- Decision: Apply redaction and truncation before writing reports/snapshots.
- Why: Prevent credential leakage and bound output size.

## D-005: Record + replay required

- Decision: Snapshot all tool outputs in record mode and enforce ordered replay matching.
- Why: Deterministic testing, offline debugging, and auditability.

## D-006: CLI-first v1

- Decision: Keep v1 interface to local CLI only.
- Why: Minimize integration surface and operational complexity.
