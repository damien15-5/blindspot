#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f .local/service.env ]]; then
  set -a
  source .local/service.env
  set +a
fi
python_bin="${BLINDSPOT_PYTHON:-.local/venv/bin/python}"
exec "$python_bin" -m uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8080}" --workers 1
