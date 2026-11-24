"""Time one daily query on the events and on N copies of them, to see how the cost grows.

    uv run python scripts/scale_probe.py 10

It writes N copies of the events to a file next to them (people and event numbers shifted, times unchanged), reads each file
with the same query, prints the size, the days and the seconds, and deletes the big file. Times vary by machine and by run.
"""

import sys
import time
from pathlib import Path

import duckdb

copies = int(sys.argv[1])
SMALL = Path("data/raw/app-events/events.csv")
BIG = Path(f"data/raw/app-events/events_x{copies}.csv")
QUERY = "SELECT CAST(event_ts AS DATE) AS day, count(*) FILTER (WHERE event_name = 'signup_complete') AS signups FROM read_csv('{}') GROUP BY day"

con = duckdb.connect()
con.execute(
    "COPY (SELECT event_id + 1000000 * k AS event_id, user_id + 100000 * k AS user_id, event_ts, event_name, platform, received_at "
    f"FROM read_csv('{SMALL}'), range({copies}) AS copies(k)) TO '{BIG}' (HEADER)"
)
for path in (SMALL, BIG):
    started = time.time()
    rows = con.execute(QUERY.format(path)).fetchall()
    print(f"{path.name}: {path.stat().st_size:,} bytes, {len(rows)} days, {time.time() - started:.2f} s")
BIG.unlink()
