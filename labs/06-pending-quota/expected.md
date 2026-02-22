# Expected Findings

## Reproduce
- `kubectl apply -f labs/06-pending-quota/manifest.yaml`
- `kubectl -n demo get pod pending-quota-demo`

## What output should show
- Pod stays `Pending`.
- `kubectl -n demo describe pod pending-quota-demo` shows `Insufficient cpu`.
- `kubectl -n demo get resourcequota demo-quota -o yaml` shows quota exists but does not block creation.

## Reasoning path
- Fact: scheduler reports `Insufficient cpu`.
- Fact: quota object exists, which can look suspicious.
- Interpretation: primary blocker is node scheduling capacity, not quota admission rejection.
- Fix: reduce CPU request and keep quota within realistic bounds.
