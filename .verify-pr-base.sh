#!/bin/bash
set -euo pipefail
BASE="agentic-ai"
HEAD=$(git branch --show-current 2>/dev/null || echo "unknown")
# When PR exists, verify its base; if no PR, we verify mechanism is set correctly
PR_BASE=$(gh pr view --json baseRefName --jq '.baseRefName' 2>/dev/null || echo "NO_PR")
if [ -n "${PR_BASE:-}" ] && [ "$PR_BASE" != "NO_PR" ]; then
  if [ "$PR_BASE" != "$BASE" ]; then
    echo "FAIL: PR base is '$PR_BASE', expected '$BASE' (HEAD: $HEAD)"
    exit 1
  else
    echo "PASS: PR base is '$PR_BASE' (HEAD: $HEAD)"
  fi
else
  echo "MECHANISM READY: target base=$BASE, current head=$HEAD, PR not yet created"
fi
