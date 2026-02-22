# Expected Findings

## Reproduce
- `kubectl apply -f labs/07-oom-probe/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod restarts repeatedly.
- `kubectl -n demo describe pod <pod>` shows `Last State: Terminated` with `Reason: OOMKilled` and exit code `137`.
- Events may also include probe `Unhealthy` warnings (`connection refused`) due to no HTTP server.

## Reasoning path
- Fact: OOMKilled/137 indicates kernel memory kill.
- Fact: probe failures are present and potentially distracting.
- Interpretation: primary cause is OOM due to unbounded memory growth; probe failures are secondary noise.
- Fix: bound memory usage and/or raise memory limit; separately fix probe only after OOM stabilization.
