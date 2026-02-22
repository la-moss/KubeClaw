# 11-noisy-pending-capacity

## Reproduce

- `kubectl apply -f labs/11-noisy-pending-capacity/manifest.yaml`
- Run triage with symptom: `Pending pod`

## Expected kubectl signals

- `pod/pending-demo` remains `Pending`
- Pod events include scheduling pressure (`Insufficient cpu`)
- Many unrelated healthy pods exist (`noise-frontend`, `noise-batch`)

## Correct reasoning path

- Facts: one target pod is Pending while noisy workloads are otherwise healthy
- Interpretation: primary failure is capacity/scheduling for `pending-demo`
- Fix: lower CPU request or increase node capacity
