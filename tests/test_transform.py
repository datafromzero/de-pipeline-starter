import duckdb
import pytest

from pipeline import transform


@pytest.fixture
def lines():
    """Build a tiny relation of (order_item_id, quantity, updated_at) rows from a list of tuples."""
    con = duckdb.connect()

    def build(*rows):
        values = ", ".join(f"({key}, {quantity}, TIMESTAMP '{updated}')" for key, quantity, updated in rows)
        return con.sql(f"SELECT * FROM (VALUES {values}) AS t(order_item_id, quantity, updated_at)")

    return build


def keep(relation):
    return sorted((key, quantity) for key, quantity, _ in relation.fetchall())


def test_a_repeated_record_is_kept_once(lines):
    rows = lines((1, 2, "2026-05-01 10:00:00"), (1, 2, "2026-05-01 10:00:00"), (2, 1, "2026-05-01 10:05:00"))
    assert keep(transform.dedupe_latest(rows)) == [(1, 2), (2, 1)]


def test_the_latest_version_wins_even_when_it_comes_first(lines):
    rows = lines((1, 2, "2026-05-03 09:00:00"), (1, 20, "2026-05-01 13:30:00"))
    assert keep(transform.dedupe_latest(rows)) == [(1, 2)]


def test_different_keys_all_stay(lines):
    rows = lines((1, 1, "2026-05-01 10:00:00"), (2, 1, "2026-05-01 10:00:00"), (3, 1, "2026-05-01 10:00:00"))
    assert keep(transform.dedupe_latest(rows)) == [(1, 1), (2, 1), (3, 1)]
