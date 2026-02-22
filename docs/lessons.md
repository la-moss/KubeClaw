# Lessons Learned

## Template

### Common failure patterns and correct interpretations

- Pattern:
- Correct interpretation:
- Evidence to require:

### Misleading signals we saw

- Signal:
- Why it misleads:
- Safer check:

### Prompt injection attempts encountered

- Attempt pattern:
- Refusal behavior:
- Rule reinforced:

### Tooling edge cases

- Edge case:
- Impact:
- Mitigation:

### Rules we never break

- Read-only only
- Tool allowlist only
- Context must be `kind-kubeclaw`
- No unredacted secret persistence
- No replay mismatch tolerance

## Initial Entry

- We enforce a strict context hard-check to prevent accidental execution against wrong clusters, especially production-like contexts that may share credentials.
- We never allow raw shell execution paths for model-directed actions because unbounded command construction breaks the primary safety boundary and undermines auditability.
- Pending-lab determinism can fail on high-core hosts if CPU requests are only moderately high; use intentionally impossible requests (for example `cpu: 1000`) so scheduler always reports `Insufficient cpu`.

## Validation Entry (2026-02-22)

- Full live sweep via OpenClaw against all 5 labs (`01`..`05`) passed.
- Classification quality: correct root-cause interpretation for CrashLoop, ImagePull, Pending, Service selector mismatch, and OOMKilled.
- Safety conformance: outputs consistently included read-only and manual-only remediation language; no namespace-scope drift observed.
- Report contract: all runs included the required 8 sections.
- Determinism note: `03-pending` required `cpu: 1000` to remain reliably Pending across high-core developer machines.

## Validation Entry (2026-02-22, Option C)

- Scale/noise scenarios need explicit "signal over volume" checks; otherwise a passing diagnosis can still hide diagnostic sprawl.
- Service-noise labs are most useful when selector mismatch remains primary while many unrelated healthy workloads coexist.
- Pending-noise labs should keep one unmistakable blocked workload (`pending-demo`) plus unrelated healthy replicas to validate focus.
- CI now enforces an observed-facts budget (`max-facts`) so report evidence remains bounded and reviewable.
