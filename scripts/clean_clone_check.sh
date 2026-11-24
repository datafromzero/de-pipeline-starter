#!/usr/bin/env bash
# The test of "someone else can run it": clone this repository into a new folder, install what it locks, and run the CI build there.
# Only what is committed is cloned, so a file that exists on your computer but not in Git makes this fail. Run it from the repository root.
set -euo pipefail

here=$(git rev-parse --show-toplevel)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone --quiet "$here" "$work/clone"
cd "$work/clone"
uv sync --locked --quiet
bash ci/dbt_ci.sh 2>&1 | grep -E "FAIL|Done"
echo "clean clone: exit status ${PIPESTATUS[0]}"
