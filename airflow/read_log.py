"""Print a task log the short way: a line for each warning, error and message of the pipeline, and the exception of a failure.

Airflow writes one JSON object for each line of a task log. Run it with: uv run python read_log.py PATH_TO_ATTEMPT_LOG
"""

import json
import sys

for line in open(sys.argv[1]):
    entry = json.loads(line)
    if entry["level"] == "info" and not entry["logger"].startswith("pipeline"):
        continue
    print(f"{entry['level']:7} {entry['logger']}: {entry['event']}")
    for error in entry.get("error_detail", []):
        print(f"        {error['exc_type']}: {error['exc_value']}")
