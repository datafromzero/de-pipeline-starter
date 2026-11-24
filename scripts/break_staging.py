"""Write a copy of the three staged tables for each of six faults, in data/broken_staging/NAME/, so that dbt can be pointed at it.

Run it with: uv run python scripts/break_staging.py
"""

import shutil

import duckdb

from pipeline.config import DATA_DIR, STAGING_DIR

OUT = DATA_DIR / "broken_staging"
TABLES = ["order_lines", "products", "stores"]
FAULTS = {
    "null_key": ("order_lines", "line 5500 loses its key", "SELECT * REPLACE (CASE WHEN order_item_id = 5500 THEN NULL ELSE order_item_id END AS order_item_id) FROM t"),
    "repeated_key": ("order_lines", "line 5500 comes twice", "SELECT * FROM t UNION ALL SELECT * FROM t WHERE order_item_id = 5500"),
    "odd_status": ("order_lines", "line 5600 has the status 'completd'", "SELECT * REPLACE (CASE WHEN order_item_id = 5600 THEN 'completd' ELSE status END AS status) FROM t"),
    "unknown_product": ("order_lines", "line 5500 sells product 99, which is not on the menu", "SELECT * REPLACE (CASE WHEN order_item_id = 5500 THEN 99 ELSE product_id END AS product_id) FROM t"),
    "extra_zero": ("order_lines", "line 6952 has a quantity of 20", "SELECT * REPLACE (CASE WHEN order_item_id = 6952 THEN 20 ELSE quantity END AS quantity) FROM t"),
    "late_opening": ("stores", "store 3 opened on May 1, a month after its first sale", "SELECT * REPLACE (CASE WHEN store_id = 3 THEN DATE '2026-05-01' ELSE opened_on END AS opened_on) FROM t"),
}

con = duckdb.connect()
for name, (table, what, sql) in FAULTS.items():
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    for other in TABLES:
        if other != table:
            shutil.copy(STAGING_DIR / f"{other}.parquet", folder / f"{other}.parquet")
    con.execute(f"CREATE OR REPLACE VIEW t AS SELECT * FROM read_parquet('{STAGING_DIR / (table + '.parquet')}')")
    con.execute(f"COPY ({sql}) TO '{folder / (table + '.parquet')}' (FORMAT parquet)")
    print(f"{folder.relative_to(DATA_DIR.parent)}: {what}")
