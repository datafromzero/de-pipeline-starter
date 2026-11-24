import logging

import duckdb
import pytest

from pipeline.checks import CheckFailed
from pipeline.gate import gate

COLUMNS = """(order_item_id BIGINT, order_id BIGINT, ordered_at TIMESTAMP, store_id BIGINT, customer_id BIGINT, status VARCHAR,
    payment_method VARCHAR, product_id BIGINT, quantity BIGINT, discount_usd DECIMAL(8, 2), updated_at TIMESTAMP, channel VARCHAR)"""


def line(key, quantity=2):
    return (key, 1, "2026-05-01 10:00:00", 1, None, "completed", "card", 1, quantity, "0.00", "2026-05-01 10:05:00", None)


@pytest.fixture
def con():
    return duckdb.connect()


def batch(con, *rows):
    con.execute(f"CREATE OR REPLACE TABLE rows_in {COLUMNS}")
    con.executemany("INSERT INTO rows_in VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return con.table("rows_in")


def test_a_line_with_a_wild_quantity_is_held_back_and_counted(con, caplog):
    with caplog.at_level(logging.INFO, logger="pipeline.gate"):
        clean = gate(con, batch(con, line(1), line(2, quantity=20), line(3, quantity=1), line(4), line(5)))
    assert sorted(key for (key,) in clean.project("order_item_id").fetchall()) == [1, 3, 4, 5]
    assert con.execute("SELECT check_name, order_item_id FROM quarantine").fetchall() == [("quantity_in_range", 2)]
    assert "5 lines read, 4 clean, 1 quarantined" in caplog.text


def test_a_missing_key_stops_the_run_before_anything_is_held(con):
    with pytest.raises(CheckFailed, match="order_item_id_not_null"):
        gate(con, batch(con, line(None), line(2, quantity=20), line(3), line(4), line(5)))
    assert con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'quarantine'").fetchall()[0][0] == 0


def test_too_many_held_lines_stop_the_run_and_hold_nothing(con):
    with pytest.raises(CheckFailed, match="over the share"):
        gate(con, batch(con, line(1), line(2, quantity=20), line(3, quantity=30), line(4, quantity=0)))
    assert con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'quarantine'").fetchall()[0][0] == 0
