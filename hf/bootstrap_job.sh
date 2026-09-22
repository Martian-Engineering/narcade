#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install --yes --no-install-recommends ca-certificates git python3 python3-pip python3-venv
rm -rf /var/lib/apt/lists/*

python3 -m venv /tmp/narcade-venv
/tmp/narcade-venv/bin/pip install --disable-pip-version-check --no-cache-dir \
  --requirement /workspace/requirements.lock \
  /workspace/dist/*.whl

exec /tmp/narcade-venv/bin/python -m jevbench --config /workspace/config.json --output-dir /outputs
