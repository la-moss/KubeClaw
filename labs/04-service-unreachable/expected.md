# Expected Findings

## Reproduce
- `kubectl apply -f labs/04-service-unreachable/manifest.yaml`
- `kubectl -n demo get svc,ep`

## What output should show
- Service `web-svc` exists but has no endpoints.
- `kubectl -n demo get endpoints web-svc` shows `<none>`.
- Deployment pods have label `app=web-wrong` while service selector is `app=web`.

## Reasoning path
- Fact: service selector matches zero pods.
- Interpretation: selector/label mismatch causes unreachable service.
- Fix: align service selector or pod labels, then verify endpoints populate.
