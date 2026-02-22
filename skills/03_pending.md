# Pending Pod

## Symptoms / signals
- Pod remains in `Pending` for prolonged period.
- No container start events.

## Minimum diagnostics (tool calls only)
- `events_tail(ns="demo", limit=30)`
- `describe_pod(ns="demo", pod="<pod>")`

## Interpretation rules (if X then Y)
- `Insufficient cpu` -> CPU request exceeds node allocatable.
- `Insufficient memory` -> memory request too high.

## Likely causes (ranked)
1. CPU/memory requests too high for kind node capacity.
2. Scheduling constraints (taints/affinity) cannot be satisfied.

## Safe remediation (text-only)
- Reduce CPU/memory requests to fit node capacity.
- Remove unnecessary scheduling constraints.

## Rollback notes
- Reapply previous workload spec with known schedulable requests.
- Verify pod transitions from `Pending` to `Running`.

## Stop conditions / when to escalate
- Escalate when cluster capacity is exhausted across namespaces.
- Stop when scheduler assigns the pod and startup proceeds.
