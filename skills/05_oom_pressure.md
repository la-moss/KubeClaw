# OOMKilled

## Symptoms / signals
- Pod restarts and `Last State` shows `OOMKilled`.
- Exit code `137` in container termination details.

## Minimum diagnostics (tool calls only)
- `events_tail(ns="demo", limit=30)`
- `describe_pod(ns="demo", pod="<pod>")`
- `top_pod(ns="demo")`

## Interpretation rules (if X then Y)
- Exit `137` + OOMKilled -> kernel terminated process for memory pressure.
- Usage near/above limit -> limit too low or leak/spike in workload.

## Likely causes (ranked)
1. Memory limit is too low for workload behavior.
2. Application has leak/unbounded buffering.

## Safe remediation (text-only)
- Increase memory limit incrementally and monitor.
- Optimize app memory usage and cap in-memory buffers.

## Rollback notes
- Revert resource settings to previous stable values.
- Confirm restart loops stop and memory usage normalizes.

## Stop conditions / when to escalate
- Escalate if OOM persists after safe limit adjustments.
- Stop when pod remains stable without `OOMKilled` events.
