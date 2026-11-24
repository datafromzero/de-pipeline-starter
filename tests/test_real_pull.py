import duckdb
import pytest

from pipeline.config import RAW_DIR
from pipeline.ingest import window_name
from pipeline.stage import staged_lines


def test_the_full_pull_makes_3287_lines():
    pages = RAW_DIR / "order_lines" / window_name(None, None)
    if not pages.exists():
        pytest.skip("land the full pull first: uv run python -m pipeline.ingest")
    assert staged_lines(duckdb.connect(), str(pages / "page-*.json")).count("*").fetchall()[0][0] == 3287
