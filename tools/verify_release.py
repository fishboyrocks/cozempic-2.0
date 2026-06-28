#!/usr/bin/env python3
"""
verify_release.py -- permanent guardrail against the exact failure that
happened with v1.0.9-alpha: code, git tag, and GitHub Release were all
pushed, and the corresponding CHANGELOG.md entry was simply never added.
Every prior verification pass checked code behavior (syntax, regression
tests, real-data extraction) and stopped there. None of them checked
whether the four artifacts a version push is supposed to produce --
the in-file version string, the git tag, the GitHub Release, and the
CHANGELOG.md entry -- actually agreed with each other afterward.

This script checks exactly that, against the real GitHub API, not
against memory of what was intended. It is read-only: it never edits or
pushes anything, it only reports PASS/FAIL for each of the four checks
below, for the version currently recorded in context_surgeon.py.

Usage:
    python3 tools/verify_release.py

Exit code 0 if all four checks pass, 1 otherwise. A non-zero exit means
the version push is NOT complete, regardless of how much code-behavior
testing was done -- documentation drift is exactly as much a release
failure as a syntax error, just slower to notice and easier to deny.
"""

import base64
import json
import re
import sys
import urllib.error
import urllib.request

REPO   = "fishboyrocks/cozempic-2.0"
BRANCH = "claude-sonnet-4.6-max"


def _gh(token: str, path: str):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def _gh_optional(token: str, path: str):
    """Like _gh, but returns None instead of raising on 404."""
    try:
        return _gh(token, path)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def verify_release(token: str) -> bool:
    print(f"Checking release consistency for {REPO} @ {BRANCH}\n")
    all_ok = True

    # ---- 1. What version does the code itself claim? -----------------------
    file_info = _gh(token, f"contents/context_surgeon.py?ref={BRANCH}")
    src = base64.b64decode(file_info["content"].replace("\n", "")).decode("utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', src)
    if not m:
        print("FAIL  context_surgeon.py has no __version__ string at all")
        return False
    version = m.group(1)
    print(f"  context_surgeon.py __version__: {version}")

    tag_name = f"v{version}"

    # ---- 2. Does a matching git tag exist, and does it point at this commit? --
    tag_ref = _gh_optional(token, f"git/refs/tags/{tag_name}")
    if tag_ref is None:
        print(f"FAIL  no git tag '{tag_name}' exists")
        all_ok = False
    else:
        tag_sha = tag_ref["object"]["sha"]
        branch_info = _gh(token, f"branches/{BRANCH}")
        branch_sha = branch_info["commit"]["sha"]
        if tag_sha == branch_sha:
            print(f"PASS  tag '{tag_name}' exists and matches branch HEAD ({tag_sha[:10]})")
        else:
            print(
                f"WARN  tag '{tag_name}' exists but points to {tag_sha[:10]}, "
                f"branch HEAD is {branch_sha[:10]} -- code has moved on since "
                f"this tag (only a real problem if version string still says "
                f"{version} with no newer tag)"
            )

    # ---- 3. Does a matching GitHub Release exist? --------------------------
    release = _gh_optional(token, f"releases/tags/{tag_name}")
    if release is None:
        print(f"FAIL  no GitHub Release exists for tag '{tag_name}'")
        all_ok = False
    else:
        print(f"PASS  GitHub Release exists: {release['html_url']}")

    # ---- 4. Does CHANGELOG.md have a matching entry? ------------------------
    changelog_info = _gh(token, f"contents/CHANGELOG.md?ref={BRANCH}")
    changelog = base64.b64decode(
        changelog_info["content"].replace("\n", "")
    ).decode("utf-8")
    pattern = re.compile(
        r"^## \[" + re.escape(version) + r"\] - \d{4}-\d{2}-\d{2}$",
        re.MULTILINE,
    )
    if pattern.search(changelog):
        print(f"PASS  CHANGELOG.md has an entry for [{version}]")
    else:
        print(
            f"FAIL  CHANGELOG.md has NO entry for [{version}] -- "
            f"this is exactly the v1.0.9-alpha failure this script exists to catch"
        )
        all_ok = False

    print()
    if all_ok:
        print("RESULT: all four artifacts consistent. Version push is complete.")
    else:
        print(
            "RESULT: inconsistent. Do not consider this version push complete "
            "until every FAIL above is resolved."
        )
    return all_ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify_release.py <github_token>", file=sys.stderr)
        sys.exit(2)
    ok = verify_release(sys.argv[1])
    sys.exit(0 if ok else 1)
