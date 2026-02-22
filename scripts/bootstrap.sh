#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> bootstrap: starting"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required"
  exit 1
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required"
  exit 1
fi
if ! command -v kind >/dev/null 2>&1; then
  echo "kind is required"
  exit 1
fi

echo "==> creating virtualenv"
python3 -m venv .venv

echo "==> installing dependencies"
".venv/bin/python" -m pip install --upgrade pip setuptools wheel
if [[ -f requirements.txt ]]; then
  ".venv/bin/pip" install -r requirements.txt
fi
if [[ -f requirements-dev.txt ]]; then
  ".venv/bin/pip" install -r requirements-dev.txt
fi
if [[ ! -f requirements.txt && ! -f requirements-dev.txt ]]; then
  ".venv/bin/pip" install pytest
fi

echo "==> ensuring kind cluster kind-kubeclaw exists"
if ! kind get clusters | grep -qx "kubeclaw"; then
  kind create cluster --name kubeclaw
fi

echo "==> selecting kubectl context"
kubectl config use-context kind-kubeclaw >/dev/null

echo "==> ensuring demo namespace exists"
kubectl get namespace demo >/dev/null 2>&1 || kubectl create namespace demo >/dev/null

if [[ "${INSTALL_METRICS_SERVER:-false}" == "true" ]]; then
  echo "==> installing metrics-server (optional)"
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
fi

echo "==> running self-check"
".venv/bin/python" -m agent.main self-check --ns demo

echo "==> bootstrap complete"
