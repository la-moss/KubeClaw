# 10-noisy-service-selector

## Reproduce

- `kubectl apply -f labs/10-noisy-service-selector/manifest.yaml`
- Run triage with symptom: `service unreachable`

## Expected kubectl signals

- `service/web-svc` exists in `demo`
- `endpoints/web-svc` has no backing addresses
- Many unrelated healthy pods/deployments are present (`noise-api`, `noise-worker`)

## Correct reasoning path

- Facts: service exists, endpoints empty, selector mismatch signal
- Interpretation: primary issue is Service selector mismatch, not overall namespace outage
- Fix: align Service selector with workload labels (`app: web-wrong` or relabel pods)
