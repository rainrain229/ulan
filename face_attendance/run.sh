#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"
if [ ! -d .venv ]; then
  echo "Creating venv..." >&2
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000