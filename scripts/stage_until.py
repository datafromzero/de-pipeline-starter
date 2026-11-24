"""Stage the order lines as the API showed them at a time, written to the staging folder.

    uv run python scripts/stage_until.py "2026-05-02 23:59:59"

The mock API must be running. The pages land in raw/ in a folder named by the window, as in DE2, and the staging
files are rewritten from them: the next dbt run sees the world as of that time. To stage the full pull again, run
`uv run python -m pipeline.stage`, which reads the pages of the full pull that DE2 landed.
"""

import logging
import sys

import duckdb

from pipeline.config import RAW_DIR
from pipeline.ingest import land, window_name
from pipeline.stage import write_staging

logging.basicConfig(level=logging.ERROR)  # the waits after a 429 or a 500 are not news here
until = sys.argv[1]
pages = land(until=until)
glob = str(RAW_DIR / "order_lines" / window_name(None, until) / "page-*.json")
write_staging(duckdb.connect(), glob)
print(f"staged the world as of {until}: {len(pages)} pages")
