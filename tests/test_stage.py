import json
import logging

import duckdb

from pipeline.stage import staged_lines

BASE = {
    "order_id": 1,
    "ordered_at": "2026-05-01 13:25:00",
    "store_id": 1,
    "customer_id": None,
    "status": "completed",
    "payment_method": "mobile",
    "product_id": 15,
    "discount_usd": "0.00",
}


def line(key, quantity):
    return {**BASE, "order_item_id": key, "quantity": quantity, "updated_at": "2026-05-01 13:30:00"}


def test_the_log_says_how_many_records_became_how_many_lines(tmp_path, caplog):
    records = [line(1, 2), line(1, 2), line(2, 1)]
    (tmp_path / "page-0001.json").write_text(json.dumps({"data": records, "next_cursor": None}))
    with caplog.at_level(logging.INFO, logger="pipeline.stage"):
        staged_lines(duckdb.connect(), str(tmp_path / "page-*.json"))
    assert "3 records read, 2 lines kept" in caplog.text
