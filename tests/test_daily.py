import json
from datetime import date, timedelta

from pipeline import daily, load
from pipeline.ingest import window_name

BASE = {
    "order_id": 1,
    "ordered_at": "2026-05-01 13:25:00",
    "store_id": 1,
    "customer_id": None,
    "status": "completed",
    "payment_method": "mobile",
    "product_id": 15,
    "discount_usd": "0.00",
    "updated_at": "2026-05-01 13:30:00",
}


def line(key, quantity):
    return {**BASE, "order_item_id": key, "quantity": quantity}


def test_a_day_is_asked_for_by_its_boundaries_one_second_early():
    assert daily.window(date(2026, 5, 2)) == ["2026-05-01 23:59:59", "2026-05-02 23:59:59"]


def test_consecutive_days_meet_without_a_gap_or_an_overlap():
    for start in (date(2026, 1, 31), date(2026, 2, 28), date(2026, 5, 1)):
        assert daily.window(start)[1] == daily.window(start + timedelta(days=1))[0]


def test_running_a_day_again_leaves_the_table_as_it_was(tmp_path):
    day = date(2026, 5, 1)
    pages = tmp_path / "raw" / "order_lines" / window_name(*daily.window(day))
    pages.mkdir(parents=True)
    records = [line(1, 2), line(2, 20), line(3, 1), line(4, 1), line(5, 3)]
    (pages / "page-0001.json").write_text(json.dumps({"data": records, "next_cursor": None}))
    con = load.connect(tmp_path / "test.duckdb")

    def run_day():
        daily.check(day, con, raw_dir=tmp_path / "raw", day_dir=tmp_path / "days")
        daily.publish(day, con, day_dir=tmp_path / "days")
        return load.fingerprint(con)

    first = run_day()
    assert first[0] == 4  # five lines read, the one with a quantity of 20 is in quarantine
    assert run_day() == first
