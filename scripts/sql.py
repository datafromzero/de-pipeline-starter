"""Run SQL against a DuckDB file and print what the last statement returns.

    uv run python scripts/sql.py FILE_OR_STATEMENT [--db PATH]

A name that ends in .sql is read as a script of several statements; anything else is one statement. The default
database is data/serving/design.duckdb, made by the script of DE12. An error prints its first line and stops with
status 1, without a traceback.
"""

import argparse
import sys
from pathlib import Path

import duckdb

from pipeline.config import SERVING_DIR


def show(columns, rows):
    cells = [[str(value) for value in row] for row in rows]
    widths = [max([len(name)] + [len(row[i]) for row in cells]) for i, name in enumerate(columns)]
    print(" | ".join(name.ljust(width) for name, width in zip(columns, widths)).rstrip())
    print("-+-".join("-" * width for width in widths))
    for row in cells:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def main():
    parser = argparse.ArgumentParser(description="Run SQL against a DuckDB file.")
    parser.add_argument("sql", help="a .sql file or one statement")
    parser.add_argument("--db", default=str(SERVING_DIR / "design.duckdb"))
    args = parser.parse_args()
    text = Path(args.sql).read_text() if args.sql.endswith(".sql") else args.sql
    con = duckdb.connect(args.db)
    try:
        statements = con.extract_statements(text)
        for statement in statements:
            result = con.execute(statement)
        if statements[-1].type == duckdb.StatementType.SELECT:
            show([column[0] for column in result.description], result.fetchall())
    except duckdb.Error as error:
        print(f"{type(error).__name__}: {str(error).splitlines()[0]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
