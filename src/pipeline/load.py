"""Load only the lines that changed since the last run, so that running it again changes nothing."""

import argparse
import logging
from datetime import timedelta

import duckdb

from pipeline.config import RAW_DIR, SERVING_DIR
from pipeline.ingest import land, window_name
from pipeline.stage import staged_lines

log = logging.getLogger("pipeline.load")
DB_PATH = SERVING_DIR / "cafe.duckdb"
LOOKBACK = timedelta(hours=1)  # ask again for the last hour before the watermark; the merge makes that safe
COLUMNS = [
    "order_item_id", "order_id", "ordered_at", "store_id", "customer_id", "status",
    "payment_method", "product_id", "quantity", "discount_usd", "updated_at", "channel",
]


def connect(path=DB_PATH):
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS order_lines (
            order_item_id BIGINT PRIMARY KEY, order_id BIGINT, ordered_at TIMESTAMP, store_id BIGINT,
            customer_id BIGINT, status VARCHAR, payment_method VARCHAR, product_id BIGINT,
            quantity BIGINT, discount_usd DECIMAL(8, 2), updated_at TIMESTAMP, channel VARCHAR
        )
    """)
    con.execute("CREATE TABLE IF NOT EXISTS load_state (source VARCHAR PRIMARY KEY, watermark TIMESTAMP)")
    return con


def fingerprint(con):
    """Rows, the sum of quantity and a short code that changes when any value of any row changes."""
    return con.execute("""
        SELECT count(*), sum(quantity), left(md5(string_agg(l::VARCHAR, '|' ORDER BY order_item_id)), 8)
        FROM order_lines l
    """).fetchall()[0]


def run(con, until=None, replay=False):
    saved = con.execute("SELECT watermark FROM load_state WHERE source = 'order_lines'").fetchall()
    watermark = None if replay or not saved else saved[0][0]
    since = None if watermark is None else (watermark - LOOKBACK).strftime("%Y-%m-%d %H:%M:%S")
    land(since, until)
    pages = RAW_DIR / "order_lines" / window_name(since, until) / "page-*.json"
    staged_lines(con, str(pages)).create_view("incoming", replace=True)
    new, newer, same = con.execute("""
        SELECT count(*) FILTER (WHERE t.order_item_id IS NULL),
               count(*) FILTER (WHERE t.order_item_id IS NOT NULL AND i.updated_at > t.updated_at),
               count(*) FILTER (WHERE t.order_item_id IS NOT NULL AND i.updated_at <= t.updated_at)
        FROM incoming i LEFT JOIN order_lines t USING (order_item_id)
    """).fetchall()[0]
    assignments = ", ".join(f"{c} = excluded.{c}" for c in COLUMNS[1:])
    con.execute("BEGIN")
    con.execute(f"""
        INSERT INTO order_lines SELECT * FROM incoming
        ON CONFLICT (order_item_id) DO UPDATE SET {assignments}
        WHERE excluded.updated_at > order_lines.updated_at
    """)
    con.execute("""
        INSERT INTO load_state SELECT 'order_lines', max(updated_at) FROM order_lines
        ON CONFLICT (source) DO UPDATE SET watermark = excluded.watermark
    """)
    con.execute("COMMIT")
    log.info("window since=%s: %d inserted, %d updated, %d unchanged", since, new, newer, same)
    rows, quantity, check = fingerprint(con)
    log.info("order_lines now: %d rows, quantity %d, fingerprint %s", rows, quantity, check)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load the order lines that changed since the last run.")
    parser.add_argument("--until", help="ask for the world as of this time, for example '2026-05-02 23:59:59'")
    parser.add_argument("--replay", action="store_true", help="ignore the saved watermark and pull everything again")
    args = parser.parse_args()
    run(connect(), until=args.until, replay=args.replay)
