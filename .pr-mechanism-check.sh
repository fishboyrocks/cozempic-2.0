#!/bin/bash
set -euo pipefail
BASE="agentic-ai"
HEAD=$(git branch --show-current)
WRAPPER="./bin/gh"
if [ -x "$WRAPPER" ]; then
  echo "ENFORCEMENT: using workspace wrapper $WRAPPER"
  echo "Creating PR from $HEAD to $BASE with explicit flags..."
  exec "$WRAPPER" pr create --base "$BASE" --head "$HEAD" "$@"
else
  echo "FAIL: wrapper $WRAPPER missing; mechanism not enforced. Aborting."
  exit 1
fi
