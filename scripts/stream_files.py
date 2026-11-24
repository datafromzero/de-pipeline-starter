"""Write the events as a stream of files, one for each day of received_at, in the order they arrived.

    uv run python scripts/stream_files.py

The files are data/raw/app-events/stream/day-001.parquet and so on. An event that reached the server on March 3 but
happened on March 1 is in the file of March 3: the file of a day holds what arrived that day, not what happened that day.
"""

import shutil
from pathlib import Path

import duckdb

EVENTS = Path("data/raw/app-events/events.csv")
OUT = Path("data/raw/app-events/stream")

shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
con = duckdb.connect()
con.execute(f"CREATE VIEW events AS SELECT * FROM read_csv('{EVENTS}')")
days = [row[0] for row in con.execute("SELECT DISTINCT CAST(received_at AS DATE) AS day FROM events ORDER BY day").fetchall()]
for number, day in enumerate(days, 1):
    con.execute(
        f"COPY (SELECT * FROM events WHERE CAST(received_at AS DATE) = DATE '{day}' ORDER BY received_at) "
        f"TO '{OUT}/day-{number:03d}.parquet' (FORMAT parquet)"
    )
print(f"{len(days)} files of events, from {days[0]} to {days[-1]}, in {OUT}")
