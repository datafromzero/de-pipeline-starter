"""Rows, units and a fingerprint of the order lines whose current version was updated from one day to another, both included.

Run it with: uv run python scripts/range_fingerprint.py 2026-05-01 2026-05-05
"""

import sys

import duckdb

from pipeline.config import SERVING_DIR

first, last = sys.argv[1], sys.argv[2]
con = duckdb.connect(str(SERVING_DIR / "cafe.duckdb"), read_only=True)
rows, units, code = con.execute(
    """
    SELECT count(*), sum(quantity), left(md5(string_agg(l::VARCHAR, '|' ORDER BY order_item_id)), 8)
    FROM order_lines l
    WHERE updated_at >= CAST(? AS DATE) AND updated_at < CAST(? AS DATE) + 1
    """,
    [first, last],
).fetchall()[0]
print(f"{first} to {last}: {rows} lines, {units} units, fingerprint {code}")
