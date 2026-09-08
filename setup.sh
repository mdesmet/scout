#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
npm ci
npm run build
echo "Ready. Run ./start.sh"
