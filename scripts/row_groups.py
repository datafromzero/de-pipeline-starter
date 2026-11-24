"""How many row groups does a filter make DuckDB read, in each of some tables?

    uv run python scripts/row_groups.py "order_date BETWEEN DATE '2026-09-01' AND DATE '2026-09-07'"
    uv run python scripts/row_groups.py "store_id = 3" lines_by_date lines_by_store

It runs EXPLAIN ANALYZE of a count with your filter on each table and prints the rows that matched and the line
"Row Groups Scanned" of the plan. Without table names it reads lines_arrival and lines_by_date, made by sql/layout.sql.
"""

import re
import sys

import duckdb

from pipeline.config import SERVING_DIR

where = sys.argv[1]
tables = sys.argv[2:] or ["lines_arrival", "lines_by_date"]

con = duckdb.connect(str(SERVING_DIR / "design.duckdb"), read_only=True)
for table in tables:
    matched = con.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchall()[0][0]
    plan = con.execute(f"EXPLAIN ANALYZE SELECT count(*) FROM {table} WHERE {where}").fetchall()[0][1]
    scanned, total = re.search(r"Row Groups Scanned: (\d+) / (\d+)", plan).groups()
    print(f"{table:14} {matched:>7,} rows matched, {scanned} of {total} row groups scanned")
