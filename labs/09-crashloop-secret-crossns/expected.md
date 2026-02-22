# Expected Findings

## Reproduce
- `kubectl apply -f labs/09-crashloop-secret-crossns/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod enters `CrashLoopBackOff`.
- Logs include `DATABASE_URL is required`.
- Secret `app-secret` exists in namespace `other`, not in `demo`.

## Reasoning path
- Fact: container exits immediately due to missing `DATABASE_URL`.
- Fact: similarly named Secret exists in another namespace.
- Interpretation: secrets are namespace-scoped; secret in `other` does not satisfy pod in `demo`.
- Fix: create required Secret in `demo` (or use correct namespace-scoped reference strategy).
