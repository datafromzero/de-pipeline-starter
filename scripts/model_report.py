"""What each dbt model is in the database, and how many rows it shows now. Run it from the dbt folder:

    uv run python ../scripts/model_report.py
    uv run python ../scripts/model_report.py stg_stores     # also: the query a view stores, if it is a view
"""

import sys

import duckdb

con = duckdb.connect("../data/serving/analytics.duckdb", read_only=True)
models = con.execute(
    "SELECT table_name, lower(table_type) FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
).fetchall()
for name, kind in models:
    rows = con.execute(f'SELECT count(*) FROM "{name}"').fetchall()[0][0]
    print(f"{name:24} {kind.replace('base ', ''):6} {rows:>6} rows")
for name in sys.argv[1:]:
    stored = con.execute("SELECT sql FROM duckdb_views() WHERE view_name = ?", [name]).fetchall()
    print(f"\n{name}: " + (stored[0][0] if stored else "a table, so no query is stored"))
