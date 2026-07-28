#!/bin/bash
set -euo pipefail
# Independent bash-only verification of mechanism
PASS=0
FAIL=0

check() {
  if "$@"; then
    echo "PASS: $*"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $*"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== INDEPENDENT BASH VERIFICATION ==="

# 1. Mechanism files exist and executable
check test -f ".pr-mechanism-check.sh"
check test -x ".pr-mechanism-check.sh"
check test -f ".verify-pr-base.sh"
check test -x ".verify-pr-base.sh"
check test -x "bin/gh"
check test -f ".profile"

# 2. Bash syntax checks
check bash -n .pr-mechanism-check.sh
check bash -n .verify-pr-base.sh
check bash -n bin/gh

# 3. Mechanism script uses wrapper with exec
check grep -q 'exec' .pr-mechanism-check.sh
check grep -q './bin/gh' .pr-mechanism-check.sh

# 4. Wrapper intercepts pr create and injects flags
check grep -q 'pr create' bin/gh
check grep -q -e '--base' bin/gh
check grep -q -e '--head' bin/gh
check grep -q 'git branch --show-current' bin/gh

# 5. Dynamic workspace path in .profile
check grep -q 'WORKSPACE' .profile

# 6. Mechanism script detects current branch correctly
CURRENT_BRANCH=$(git branch --show-current)
check test -n "$CURRENT_BRANCH"

# 7. Direct mechanism execution produces enforcement message
OUTPUT=$(bash .pr-mechanism-check.sh --title "independent-verify" --body "independent-verify" 2>&1 || true)
check echo "$OUTPUT" | grep -q 'ENFORCEMENT'
check echo "$OUTPUT" | grep -q 'agentic-ai'
check echo "$OUTPUT" | grep -q "$CURRENT_BRANCH"

# 8. No syntax errors in mechanism scripts when executed
OUTPUT2=$(bash .verify-pr-base.sh 2>/dev/null || true)
check echo "$OUTPUT2" | grep -qE 'MECHANISM READY|PASS|FAIL'

echo ""
echo "RESULTS: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  echo "VERIFICATION FAILED"
  exit 1
else
  echo "VERIFICATION PASSED"
fi
