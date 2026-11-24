"""Write five broken copies of the staged order lines into data/broken/, one fault in each.

Run it with: uv run python scripts/break_data.py
"""

import duckdb

from pipeline.config import DATA_DIR, STAGING_DIR

SOURCE = STAGING_DIR / "order_lines.parquet"
OUT = DATA_DIR / "broken"
BREAKS = {
    "null_key": ("line 5500 loses its key", "SELECT * REPLACE (CASE WHEN order_item_id = 5500 THEN NULL ELSE order_item_id END AS order_item_id) FROM lines"),
    "repeated_key": (
        "line 5500 comes twice, with two versions",
        "SELECT * FROM lines UNION ALL SELECT * REPLACE (updated_at + INTERVAL 1 DAY AS updated_at) FROM lines WHERE order_item_id = 5500",
    ),
    "extra_zero": ("line 6952 has a quantity of 20", "SELECT * REPLACE (CASE WHEN order_item_id = 6952 THEN 20 ELSE quantity END AS quantity) FROM lines"),
    "odd_status": ("line 5600 has the status 'completd'", "SELECT * REPLACE (CASE WHEN order_item_id = 5600 THEN 'completd' ELSE status END AS status) FROM lines"),
    "silent_day": ("every line of March 14 is missing", "SELECT * FROM lines WHERE ordered_at::DATE <> DATE '2026-03-14'"),
}

OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.execute(f"CREATE VIEW lines AS SELECT * FROM read_parquet('{SOURCE}')")
for name, (what, sql) in BREAKS.items():
    path = OUT / f"{name}.parquet"
    con.execute(f"COPY ({sql}) TO '{path}' (FORMAT parquet)")
    rows = con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchall()[0][0]
    print(f"{path.relative_to(DATA_DIR.parent)}: {rows} rows; {what}")
