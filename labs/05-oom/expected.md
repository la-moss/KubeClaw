# Expected Findings

## Reproduce
- `kubectl apply -f labs/05-oom/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod restarts repeatedly.
- `kubectl -n demo describe pod oom-demo` shows `Last State: Terminated` and `Reason: OOMKilled`.
- Exit code is `137`.

## Reasoning path
- Fact: process is killed by OOM with low memory limit.
- Interpretation: memory limit is too low for workload behavior.
- Fix: raise memory limit and/or reduce memory usage.
