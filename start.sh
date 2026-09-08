#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Run ./setup.sh first."
  exit 1
fi
if [ ! -f dist/index.html ]; then
  echo "Build the web workspace first: npm run build"
  exit 1
fi
echo "Opportunity Scout: http://127.0.0.1:8765"
exec .venv/bin/python -m uvicorn scout.app:app --host 127.0.0.1 --port 8765
