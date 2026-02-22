# Service Unreachable

## Symptoms / signals
- Service exists but requests fail/time out.
- Endpoint list is empty or missing expected pod IPs.

## Minimum diagnostics (tool calls only)
- `events_tail(ns="demo", limit=30)`
- `get_yaml(kind="svc", ns="demo", name="<service>")`
- `get_yaml(kind="ep", ns="demo", name="<service>")`

## Interpretation rules (if X then Y)
- Empty endpoints + selector mismatch -> service points to no pods.
- Endpoints populated but failures persist -> check ports/readiness.

## Likely causes (ranked)
1. Selector/label mismatch yields zero endpoints.
2. `targetPort` does not match container port.

## Safe remediation (text-only)
- Align service selector with deployment/pod labels.
- Verify `targetPort` maps to actual container port.

## Rollback notes
- Revert service spec to prior selector/port config.
- Confirm endpoints repopulate and traffic succeeds.

## Stop conditions / when to escalate
- Escalate if endpoints are present but traffic still fails (possible policy/network issue).
- Stop when endpoints populate and in-cluster service checks pass.
