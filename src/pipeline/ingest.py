"""Land the order lines from the API, page by page, exactly as they arrive."""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

from pipeline.config import API_URL, RAW_DIR

log = logging.getLogger("pipeline.ingest")


def wait_time(response, attempt, base=0.5):
    """How long to wait before trying again: what the server asked for, else a doubling wait."""
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return base * 2 ** (attempt - 1)


def fetch_page(params, attempts=5, sleep=time.sleep):
    """Ask for one page. Try again after a 429 or a 5xx, and fail at once on any other error."""
    for attempt in range(1, attempts + 1):
        response = requests.get(f"{API_URL}/order-lines", params=params, timeout=10)
        if response.status_code == 200:
            return response
        retryable = response.status_code == 429 or response.status_code >= 500
        if not retryable or attempt == attempts:
            response.raise_for_status()
        pause = wait_time(response, attempt)
        log.warning("HTTP %s, waiting %.1f s (attempt %d of %d)", response.status_code, pause, attempt, attempts)
        sleep(pause)


def window_name(since, until):
    """A folder name for a request window: the same request always lands in the same folder."""
    text = f"since={since or 'start'}_until={until or 'now'}"
    return text.replace(":", "-").replace(" ", "T")


def land(since=None, until=None, raw_dir=RAW_DIR):
    """Write every page of a window to raw/order_lines/<window>/ and a manifest beside the pages."""
    folder = raw_dir / "order_lines" / window_name(since, until)
    folder.mkdir(parents=True, exist_ok=True)
    manifest, cursor, number = [], None, 1
    while True:
        response = fetch_page({"since": since, "until": until, "cursor": cursor})
        path = folder / f"page-{number:04d}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(response.content)  # the bytes as they arrived
        os.replace(temporary, path)  # a page is whole or absent, never half written
        manifest.append(
            {
                "file": path.name,
                "bytes": len(response.content),
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "landed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        cursor = response.json()["next_cursor"]
        if cursor is None:
            break
        number += 1
    (folder / "_manifest.json").write_text(json.dumps(manifest, indent=1))
    log.info("landed %d pages in %s", len(manifest), folder.name)
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    land()
