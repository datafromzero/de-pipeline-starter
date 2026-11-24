"""Measure the same order lines as JSON, CSV and Parquet, and as Parquet split into partitions.

Run it with one word: formats, month or day.
"""

import re
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

import duckdb

from pipeline.config import RAW_DIR, STAGING_DIR
from pipeline.ingest import window_name
from pipeline.stage import LINE_FIELDS

QUERY = "SELECT store_id, sum(quantity) FROM {} GROUP BY store_id"
RUNS = 7  # each time is the median of this many runs
LINES = STAGING_DIR / "order_lines.parquet"
SCHEMES = {  # name: (partition key, a filter for May that matches it)
    "nothing": (None, "ordered_at >= TIMESTAMP '2026-05-01' AND ordered_at < TIMESTAMP '2026-06-01'"),
    "month": ("date_trunc('month', ordered_at)::DATE", "part = DATE '2026-05-01'"),
    "day": ("ordered_at::DATE", "part BETWEEN DATE '2026-05-01' AND DATE '2026-05-31'"),
}


def median_ms(con, sql):
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        con.sql(sql).fetchall()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times)


def files_scanned(con, sql):
    """The 'Scanning Files: a/b' line of the plan: how many files the query opened, of how many."""
    plan = con.execute(f"EXPLAIN ANALYZE {sql}").fetchall()[0][1]
    found = re.search(r"Scanning Files: (\d+/\d+)", plan)
    return found.group(1) if found else "n/a"


def folder_bytes(folder):
    files = [path for path in Path(folder).rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def compare_formats(con, folder):
    pages = RAW_DIR / "order_lines" / window_name(None, None)
    con.read_parquet(str(LINES)).write_csv(str(folder / "lines.csv"))
    json_lines = f"read_json('{pages}/page-*.json', columns = {{data: '{LINE_FIELDS}[]'}})"
    sources = {
        "json pages": (f"(SELECT l.* FROM (SELECT unnest(data) AS l FROM {json_lines}))", folder_bytes(pages)[1] - (pages / "_manifest.json").stat().st_size),
        "csv": (f"read_csv('{folder / 'lines.csv'}')", (folder / "lines.csv").stat().st_size),
        "parquet": (f"read_parquet('{LINES}')", LINES.stat().st_size),
    }
    print(f"{'format':<12}{'bytes':>9}{'read ms':>9}")
    for name, (source, size) in sources.items():
        print(f"{name:<12}{size:>9,}{median_ms(con, QUERY.format(source)):>9.1f}")
    for name in ("csv", "parquet"):
        columns = con.sql(f"DESCRIBE SELECT discount_usd, ordered_at FROM {sources[name][0]}").fetchall()
        print(f"{name} gives back: {[(column[0], column[1]) for column in columns]}")


def compare_partitions(con, folder, schemes):
    print(f"{'partitioned by':<16}{'files':>6}{'bytes':>9}{'all ms':>8}{'May ms':>8}{'May files':>11}")
    for name in schemes:
        key, may_filter = SCHEMES[name]
        target = folder / f"by_{name}"
        if key:
            con.execute(f"COPY (SELECT *, {key} AS part FROM '{LINES}') TO '{target}' (FORMAT parquet, PARTITION_BY (part))")
        else:
            target.mkdir()
            shutil.copy(LINES, target)
        reading = f"read_parquet('{target}/**/*.parquet', hive_partitioning = true)"
        files, size = folder_bytes(target)
        in_may = QUERY.format(f"(SELECT * FROM {reading} WHERE {may_filter})")
        print(f"{name:<16}{files:>6}{size:>9,}{median_ms(con, QUERY.format(reading)):>8.1f}{median_ms(con, in_may):>8.1f}{files_scanned(con, in_may):>11}")


if __name__ == "__main__":
    connection = duckdb.connect()
    with tempfile.TemporaryDirectory() as scratch:
        if sys.argv[1] == "formats":
            compare_formats(connection, Path(scratch))
        else:
            compare_partitions(connection, Path(scratch), list(SCHEMES)[: 2 if sys.argv[1] == "month" else 3])
