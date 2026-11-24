"""Rows of each dbt model and how many different values its grain has. Run it from the dbt folder: uv run python ../scripts/dbt_counts.py"""

import duckdb

MODELS = {
    "stg_order_lines": "order_line_id",
    "int_order_lines_priced": "order_line_id",
    "fct_store_daily_sales": "store_id || '|' || order_date",
}

con = duckdb.connect("../data/serving/analytics.duckdb", read_only=True)
for model, grain in MODELS.items():
    rows, distinct = con.execute(f"SELECT count(*), count(DISTINCT {grain}) FROM {model}").fetchall()[0]
    print(f"{model}: {rows} rows, {distinct} different grains")
