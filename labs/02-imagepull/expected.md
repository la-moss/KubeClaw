# Expected Findings

## Reproduce
- `kubectl apply -f labs/02-imagepull/manifest.yaml`
- `kubectl -n demo get pods`

## What output should show
- Pod status becomes `ErrImagePull` then `ImagePullBackOff`.
- `kubectl -n demo describe pod <pod>` includes image pull failure for `nginx:does-not-exist`.

## Reasoning path
- Fact: image cannot be pulled from registry.
- Interpretation: image tag is invalid/nonexistent.
- Fix: use a valid image tag and redeploy.
