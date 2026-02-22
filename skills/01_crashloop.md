# CrashLoopBackOff

## Symptoms / signals
- Pod status shows `CrashLoopBackOff`.
- Restart count increases rapidly.

## Minimum diagnostics (tool calls only)
- `events_tail(ns="demo", limit=30)`
- `describe_pod(ns="demo", pod="<pod>")`
- `logs(ns="demo", pod="<pod>", previous=True, tail=200)`

## Interpretation rules (if X then Y)
- Logs mention missing env/config -> startup dependency not provided.
- Exit code `1` with immediate restarts -> app boot failure, not scheduling issue.

## Likely causes (ranked)
1. Missing required env var such as `DATABASE_URL`.
2. Invalid entrypoint/command.

## Safe remediation (text-only)
- Add required env var/config and roll out the workload.
- Keep changes minimal and verify restart count stops increasing.

## Rollback notes
- Revert deployment to previous manifest revision.
- Verify pod becomes `Running` and restarts stabilize at `0`.

## Stop conditions / when to escalate
- Escalate if crashes persist after env/config correction.
- Stop when restart count stabilizes and readiness is healthy.
