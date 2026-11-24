"""What would a warehouse bill for this query: the blocks it reads and the logical bytes of the columns in them.

    uv run python scripts/blocks.py TABLE COLUMNS [--range COLUMN LOW HIGH]... [--db PATH]

    uv run python scripts/blocks.py lines_by_date store_id,quantity --range order_date 2026-09-01 2026-09-07

A block here is one DuckDB row group of 122,880 rows, the stand-in for a storage block of a warehouse. A block is read
unless its smallest and largest value of a filtered column rule the filter out (the rule of a zone map). The line
"engine" is the count that the plan of DuckDB reports for the same filter; the script stops if the two differ.
Bytes are logical bytes, counted as BigQuery counts them for the columns in COLUMNS: 8 for a whole number, a date or a
timestamp, 16 for a decimal, 1 for a boolean, 2 plus the UTF-8 size for text. The default database is data/serving/design.duckdb.
"""

import argparse
import re
import sys

import duckdb

from pipeline.config import SERVING_DIR

BLOCK = 122_880
EIGHT = ("INTEGER", "BIGINT", "DATE", "TIMESTAMP", "DOUBLE", "SMALLINT", "TINYINT")


def size_sql(column, kind):
    """The SQL that adds up the logical bytes of one column."""
    if kind in EIGHT:
        return f"8 * count({column})"
    if kind.startswith("DECIMAL"):
        return f"16 * count({column})"  # a decimal loads as NUMERIC, 16 logical bytes
    if kind == "BOOLEAN":
        return f"count({column})"
    if kind == "VARCHAR":
        return f"coalesce(sum(2 + strlen({column})), 0)"
    sys.exit(f"{column}: no BigQuery size for {kind}")


def main():
    parser = argparse.ArgumentParser(description="Blocks read and logical bytes of a query.")
    parser.add_argument("table")
    parser.add_argument("columns", help="the columns the query reads, separated by commas")
    parser.add_argument("--range", nargs=3, action="append", default=[], metavar=("COLUMN", "LOW", "HIGH"))
    parser.add_argument("--db", default=str(SERVING_DIR / "design.duckdb"))
    args = parser.parse_args()
    con = duckdb.connect(args.db, read_only=True)
    types = {row[0]: row[1] for row in con.execute(f"DESCRIBE {args.table}").fetchall()}
    reads = args.columns.split(",")
    for column in reads + [r[0] for r in args.range]:
        if column not in types:
            sys.exit(f"{args.table} has no column {column}")
    # A block is read unless the smallest and the largest value of a filtered column rule the filter out.
    keep = " AND ".join(f"max({c}) >= CAST('{lo}' AS {types[c]}) AND min({c}) <= CAST('{hi}' AS {types[c]})" for c, lo, hi in args.range) or "true"
    blocks = con.execute(f"SELECT rowid // {BLOCK} AS block, {keep} AS keep FROM {args.table} GROUP BY block ORDER BY block").fetchall()
    read = [block for block, kept in blocks if kept]
    scanned, total = len(blocks), len(blocks)  # a query with no filter reads every block, and its plan prints no count
    if args.range:
        where = " AND ".join(f"{c} BETWEEN '{lo}' AND '{hi}'" for c, lo, hi in args.range)
        plan = con.execute(f"EXPLAIN ANALYZE SELECT count(*) FROM {args.table} WHERE {where}").fetchall()[0][1]
        scanned, total = map(int, re.search(r"Row Groups Scanned: (\d+) / (\d+)", plan).groups())
    if (scanned, total) != (len(read), len(blocks)):
        sys.exit(f"The rule reads {len(read)} of {len(blocks)} blocks, the engine {scanned} of {total}: the rule is wrong for this filter.")
    bytes_sql = " + ".join(size_sql(c, types[c]) for c in reads)
    listed = ", ".join(str(b) for b in read) or "-1"
    rows_read, bytes_read = con.execute(f"SELECT count(*), {bytes_sql} FROM {args.table} WHERE rowid // {BLOCK} IN ({listed})").fetchone()
    bytes_all = con.execute(f"SELECT {bytes_sql} FROM {args.table}").fetchone()[0]
    print(f"{args.table}: {len(read)} of {len(blocks)} blocks read ({rows_read:,} rows); engine: {scanned} of {total}")
    print(f"columns {args.columns}: {bytes_read or 0:,} bytes read of {bytes_all:,} ({100 * (bytes_read or 0) / bytes_all:.1f} percent)")


if __name__ == "__main__":
    main()
