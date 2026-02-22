# Expected Findings

## Reproduce
- `kubectl apply -f labs/01-crashloop/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod from `crashloop-demo` deployment enters `CrashLoopBackOff`.
- `kubectl -n demo logs <pod>` includes `DATABASE_URL is required`.
- `kubectl -n demo describe pod <pod>` shows repeated restarts.

## Reasoning path
- Fact: process exits quickly with missing env message.
- Interpretation: required env var `DATABASE_URL` is unset.
- Fix: add `DATABASE_URL` env var in deployment and roll out.
