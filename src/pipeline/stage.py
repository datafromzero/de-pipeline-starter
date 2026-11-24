"""Turn the raw pages into typed, de-duplicated tables in the staging layer."""

import duckdb

from pipeline.config import RAW_DIR, SOURCE_FILES, STAGING_DIR
from pipeline.ingest import window_name

LINE_FIELDS = """STRUCT(
    order_item_id BIGINT, order_id BIGINT, ordered_at TIMESTAMP, store_id BIGINT, customer_id BIGINT,
    status VARCHAR, payment_method VARCHAR, product_id BIGINT, quantity BIGINT, discount_usd DECIMAL(8, 2),
    updated_at TIMESTAMP, channel VARCHAR
)"""


def staged_lines(con, pages_glob):
    """One row for each order line: typed columns, and the latest version when a key repeats."""
    return con.sql(f"""
        WITH pages AS (
            SELECT unnest(data) AS line
            FROM read_json('{pages_glob}', columns = {{data: '{LINE_FIELDS}[]'}})
        ),
        lines AS (SELECT line.* FROM pages)
        SELECT * FROM lines
        QUALIFY row_number() OVER (PARTITION BY order_item_id ORDER BY updated_at DESC) = 1
        ORDER BY order_item_id
    """)


def write_staging(con, pages_glob=None, out_dir=STAGING_DIR):
    """Write order_lines, products and stores as Parquet files in the staging folder."""
    pages_glob = pages_glob or str(RAW_DIR / "order_lines" / window_name(None, None) / "page-*.json")
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = staged_lines(con, pages_glob)
    lines.write_parquet(str(out_dir / "order_lines.parquet"))
    for name, types in {
        "products": {"product_id": "INTEGER", "unit_price_usd": "DECIMAL(6, 2)"},
        "stores": {"store_id": "INTEGER", "opened_on": "DATE"},
    }.items():
        csv_path = SOURCE_FILES / f"{name}.csv"
        con.read_csv(str(csv_path), dtype=types).write_parquet(str(out_dir / f"{name}.parquet"))


if __name__ == "__main__":
    write_staging(duckdb.connect())
