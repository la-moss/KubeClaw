# ImagePullBackOff

## Symptoms / signals
- Pod shows `ErrImagePull` or `ImagePullBackOff`.
- Pull failures repeat with back-off delay.

## Minimum diagnostics (tool calls only)
- `events_tail(ns="demo", limit=30)`
- `describe_pod(ns="demo", pod="<pod>")`

## Interpretation rules (if X then Y)
- `not found` in pull errors -> wrong image/tag.
- `unauthorized`/`denied` -> missing or invalid pull credentials.

## Likely causes (ranked)
1. Nonexistent image tag.
2. Missing or invalid pull secret.

## Safe remediation (text-only)
- Correct image reference and tag.
- Add or fix `imagePullSecrets` for private images.

## Rollback notes
- Revert to last known-good image digest/tag.
- Confirm pod reaches `Running` without pull retries.

## Stop conditions / when to escalate
- Escalate when registry/network failures affect multiple workloads.
- Stop when pod pulls image successfully and enters `Running`.
