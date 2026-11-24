"""One day of the pipeline, in three steps that a scheduler can run, retry and rerun on their own.

A step takes the day and nothing else: the lines that were updated during that calendar day.
"""

import argparse
import logging
from datetime import date, datetime, timedelta

from pipeline import load
from pipeline.config import RAW_DIR, STAGING_DIR
from pipeline.gate import gate
from pipeline.ingest import land, window_name
from pipeline.stage import staged_lines

log = logging.getLogger("pipeline.daily")
DAY_DIR = STAGING_DIR / "days"


def window(day):
    """The API's since and until for the lines updated during one day. since is exclusive and until is inclusive, so both stop one second early."""
    start = datetime.combine(day, datetime.min.time())
    return [(moment - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S") for moment in (start, start + timedelta(days=1))]


def extract(day, raw_dir=RAW_DIR):
    """Land the raw pages of the day. The same day lands in the same folder."""
    since, until = window(day)
    pages = land(since, until, raw_dir=raw_dir)
    log.info("%s: %d pages landed", day, len(pages))


def check(day, con, raw_dir=RAW_DIR, day_dir=DAY_DIR):
    """Stage the day, let the contract's checks decide, and keep the clean lines in a file of their own."""
    since, until = window(day)
    pages = raw_dir / "order_lines" / window_name(since, until) / "page-*.json"
    day_dir.mkdir(parents=True, exist_ok=True)
    gate(con, staged_lines(con, str(pages))).write_parquet(str(day_dir / f"{day}.parquet"))


def publish(day, con, day_dir=DAY_DIR):
    """Merge the clean lines of the day into order_lines. The watermark of the incremental load is left alone."""
    clean = con.read_parquet(str(day_dir / f"{day}.parquet"))
    new, newer, same = load.merge(con, clean, save_watermark=False)
    log.info("%s: %d inserted, %d updated, %d unchanged", day, new, newer, same)


def run_step(step, day):
    """Run one step for one day. This is the only place the DAG file has to know about."""
    if step == "extract":
        return extract(day)
    con = load.connect()
    try:
        {"check": check, "publish": publish}[step](day, con)
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run the steps of the pipeline for one day.")
    parser.add_argument("day", type=date.fromisoformat, help="the day whose updated lines to load, for example 2026-05-02")
    parser.add_argument("--step", choices=["extract", "check", "publish"], help="run only this step")
    args = parser.parse_args()
    for step in [args.step] if args.step else ["extract", "check", "publish"]:
        run_step(step, args.day)
