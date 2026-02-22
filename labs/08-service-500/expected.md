# Expected Findings

## Reproduce
- `kubectl apply -f labs/08-service-500/manifest.yaml`
- `kubectl -n demo get pods,svc,ep`

## What output should show
- Pod is `Running` and `Ready`.
- Service has populated endpoints.
- Service path checks (for example `/status/500`) return HTTP 500 while network routing remains healthy.

## Reasoning path
- Fact: service routing works (endpoints present).
- Fact: application endpoint returns 500.
- Interpretation: this is an application-level failure, not a Kubernetes service wiring failure.
- Fix: inspect app logs/config for request handling or backend dependency errors.
