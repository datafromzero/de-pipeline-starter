"""Checks that come from the contract. A check is a query that returns the bad rows: no rows, no problem."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb

from pipeline.config import ROOT

CONTRACT = ROOT / "contracts" / "order_lines.json"


class CheckFailed(Exception):
    """A rule whose failure must stop the run."""


def load_contract(path=CONTRACT):
    return json.loads(Path(path).read_text())


def row_checks(contract):
    """One (name, action, SQL) for each rule about single rows. {t} stands for the table; the SQL returns the rows that break the rule."""
    key = contract["key"]
    checks = [(f"{key}_unique", "stop", f"SELECT {key}, count(*) AS copies FROM {{t}} GROUP BY {key} HAVING count(*) > 1")]
    for column, rule in contract["columns"].items():
        action = rule.get("on_fail", "stop")
        if not rule["nullable"]:
            checks.append((f"{column}_not_null", "stop", f"SELECT * FROM {{t}} WHERE {column} IS NULL"))
        if "accepted" in rule:
            values = ", ".join(f"'{value}'" for value in rule["accepted"])
            checks.append((f"{column}_accepted", action, f"SELECT * FROM {{t}} WHERE {column} NOT IN ({values})"))
        if "min" in rule:
            checks.append((f"{column}_in_range", action, f"SELECT * FROM {{t}} WHERE {column} NOT BETWEEN {rule['min']} AND {rule['max']}"))
    return checks + [(rule["name"], rule["on_fail"], rule["bad_rows"]) for rule in contract.get("rules", [])]


def table_checks(contract, as_of):
    """Rules about a whole table: how new its newest line is and how many lines each day holds."""
    hours, per_day = contract["freshness_hours"], contract["lines_per_day"]
    return [
        ("fresh", "warn", f"SELECT max(updated_at) AS newest FROM {{t}} HAVING max(updated_at) < TIMESTAMP '{as_of}' - INTERVAL {hours} HOUR"),
        (
            "lines_per_day",
            "warn",
            f"""
            SELECT g.day, count(t.order_item_id) AS lines
            FROM (SELECT unnest(generate_series(min(ordered_at)::DATE, max(ordered_at)::DATE, INTERVAL 1 DAY))::DATE AS day FROM {{t}}) g
            LEFT JOIN {{t}} t ON t.ordered_at::DATE = g.day
            GROUP BY g.day
            HAVING count(t.order_item_id) NOT BETWEEN {per_day['min']} AND {per_day['max']}
            """,
        ),
    ]


def run_checks(con, table, checks):
    """Run every check on a table or view. Return (name, action, first column, its values in the bad rows) for each."""
    results = []
    for name, action, sql in checks:
        bad = con.sql(sql.format(t=table))
        results.append((name, action, bad.columns[0], [row[0] for row in bad.fetchall()]))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Parquet files of order lines against the contract.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--as-of", default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), help="the time 'fresh' is measured from")
    parser.add_argument("--contract", default=CONTRACT)
    args = parser.parse_args()
    contract, con, failures = load_contract(args.contract), duckdb.connect(), 0
    for file in args.files:
        con.execute(f"CREATE OR REPLACE VIEW lines AS SELECT * FROM read_parquet('{file}')")
        results = run_checks(con, "lines", row_checks(contract) + table_checks(contract, args.as_of))
        print(file)
        for name, action, column, values in results:
            if values:
                failures += 1
                print(f"  FAIL {name} ({action}): {len(values)} bad rows, {column} {', '.join(str(v) for v in values[:3])}")
        print(f"  {sum(1 for *_, values in results if not values)} of {len(results)} checks passed")
    sys.exit(1 if failures else 0)
