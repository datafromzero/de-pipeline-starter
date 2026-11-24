"""Download the events of the app-events dataset from its release tag, to data/raw/app-events/events.csv.

    uv run python scripts/fetch_app_events.py
"""

from pathlib import Path

import requests

URL = "https://raw.githubusercontent.com/datafromzero/datafromzero.github.io/v0.2.0/datasets/app-events/v1/events.csv"
TARGET = Path("data/raw/app-events/events.csv")

response = requests.get(URL, timeout=60)
response.raise_for_status()
TARGET.parent.mkdir(parents=True, exist_ok=True)
TARGET.write_bytes(response.content)
events = response.content.count(b"\n") - 1  # one line is the header
print(f"{TARGET}: {len(response.content):,} bytes, {events:,} events")
