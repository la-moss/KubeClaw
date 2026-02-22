# Expected Findings

## Reproduce
- `kubectl apply -f labs/03-pending/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod stays `Pending`.
- `kubectl -n demo describe pod pending-demo` shows `Insufficient cpu`.
- Request (`cpu: 1000`) is intentionally impossible on kind to keep this lab deterministic.

## Reasoning path
- Fact: scheduler rejects pod for CPU request.
- Interpretation: requested CPU exceeds kind node allocatable capacity.
- Fix: lower CPU request (for example `100m`) and reapply.
