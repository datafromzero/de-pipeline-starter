#!/usr/bin/env bash
# The CI build of the dbt project, from nothing: land the data, stage it, replay the partner's file, then build every
# model, snapshot and test. Run it from the repository root, on your laptop or in GitHub Actions. It writes only to data/ci/.
set -euo pipefail

export DATA_DIR="$PWD/data/ci"
export STAGING_DIR="$DATA_DIR/staging"
export PARTNER_DIR="$DATA_DIR/partner"
export CI_DB="$DATA_DIR/ci.duckdb"
rm -rf "$DATA_DIR"
mkdir -p "$DATA_DIR"

api_up() {
    uv run python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null
}

# The mock API of the lessons; if it already runs in your first terminal, this uses that one.
if ! api_up; then
    uv run python mock_api.py --retry-after 0 > "$DATA_DIR/api.log" 2>&1 &
    api=$!
    trap 'kill "$api"' EXIT
    until api_up; do sleep 1; done
fi

uv run python -m pipeline.ingest
uv run python -m pipeline.stage

# The snapshot keeps history only from the runs it has seen, so CI shows it the partner's file twice: first, then as it is now.
uv run python scripts/partner_files.py 1
(cd dbt && uv run dbt snapshot --target ci)
uv run python scripts/partner_files.py 3
(cd dbt && uv run dbt build --target ci)
