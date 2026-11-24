"""A mock sales API for the pipeline lessons. Run it with: uv run python mock_api.py

It serves the lines of the cafe-sales orders from `mock_api_data/` at
GET /order-lines, a page at a time, and fails on purpose in ways a real source does.
Every fault is a pure function of the seed, so a run reproduces. The contract is in README.md.
"""

import argparse
import base64
import csv
import json
import random
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse

SEED = 2026
PAGE_SIZE = 100  # the default and the largest page
RATE_429 = 0.10  # share of pages whose first request gets 429
RATE_500 = 0.05  # share of pages whose first request gets 500
REPEAT_FAULT = 0.30  # chance that the second request fails the same way
DRIFT_FROM = "2026-05-01 00:00:00"  # versions updated from here on carry a `channel` field
POST_DELAY = timedelta(minutes=5)  # the till posts a line five minutes after the order time
FORMAT = "%Y-%m-%d %H:%M:%S"
DATA = Path(__file__).resolve().parent / "mock_api_data"


def load_versions(seed=SEED, data=DATA):
    """Every version of every line, as (updated_at, record) pairs in time order.

    A line has one version, plus a second one for 12 corrected lines: the extra-zero
    line (quantity 20 corrected to 2) and 11 lines chosen by the seed (quantity plus 1).
    """
    with open(data / "orders.csv", newline="") as f:
        orders = {int(r["order_id"]): r for r in csv.DictReader(f)}
    with open(data / "order_items.csv", newline="") as f:
        items = list(csv.DictReader(f))
    rng = random.Random(f"{seed}:corrections")
    ordinary = [r["order_item_id"] for r in items if int(r["quantity"]) <= 2]
    corrected = set(rng.sample(ordinary, 11))
    versions = []
    for item in items:
        order = orders[int(item["order_id"])]
        ordered_at = datetime.strptime(order["ordered_at"], FORMAT)
        record = {
            "order_item_id": int(item["order_item_id"]),
            "order_id": int(order["order_id"]),
            "ordered_at": order["ordered_at"],
            "store_id": int(order["store_id"]),
            "customer_id": int(order["customer_id"]) if order["customer_id"] else None,
            "status": order["status"],
            "payment_method": order["payment_method"],
            "product_id": int(item["product_id"]),
            "quantity": int(item["quantity"]),
            "discount_usd": item["discount_usd"],
        }
        first = dict(record, updated_at=(ordered_at + POST_DELAY).strftime(FORMAT))
        versions.append((first["updated_at"], first))
        if item["order_item_id"] in corrected or record["quantity"] == 20:
            days = 2 if record["quantity"] == 20 else rng.randint(1, 3)
            quantity = 2 if record["quantity"] == 20 else record["quantity"] + 1
            second = dict(first, quantity=quantity)
            second["updated_at"] = (ordered_at + timedelta(days=days) + POST_DELAY).strftime(FORMAT)
            versions.append((second["updated_at"], second))
    versions.sort(key=lambda v: (v[0], v[1]["order_item_id"]))
    return versions


def channel_of(seed, order_id):
    return "app" if random.Random(f"{seed}:channel:{order_id}").random() < 0.3 else "counter"


def select(versions, since=None, until=None):
    """The current version of each line as of `until`, kept when updated after `since`."""
    current = {}
    for updated_at, record in versions:
        if until is None or updated_at <= until:
            current[record["order_item_id"]] = (updated_at, record)
    kept = [v for v in current.values() if since is None or v[0] > since]
    kept.sort(key=lambda v: (v[0], v[1]["order_item_id"]))
    return kept


def repeat_index(seed):
    """The position of the record that is sent twice: the last one of a page of 100."""
    return 100 * random.Random(f"{seed}:repeat").randint(5, 25) - 1


def with_repeat(kept, seed=SEED):
    """Repeat one record right after itself: the last record of one page is also the first of the next."""
    at = repeat_index(seed)
    if len(kept) <= at:
        return kept
    return kept[: at + 1] + [kept[at]] + kept[at + 1 :]


def planned_fault(seed, offset, failures_so_far):
    """The status code the request for the page at `offset` must get, or None."""
    rng = random.Random(f"{seed}:{offset}")
    first, again = rng.random(), rng.random()
    kind = 429 if first < RATE_429 else 500 if first < RATE_429 + RATE_500 else None
    if kind is None or failures_so_far >= 2:
        return None
    return kind if failures_so_far == 0 or again < REPEAT_FAULT else None


def render(seed, pair):
    updated_at, record = pair
    if updated_at >= DRIFT_FROM:
        record = dict(record, channel=channel_of(seed, record["order_id"]))
    return record


def parse_time(text):
    return datetime.fromisoformat(text).strftime(FORMAT)


class Handler(BaseHTTPRequestHandler):
    server_version = "MockCafeAPI/1.0"

    def log_message(self, fmt, *args):
        if self.server.verbose:
            super().log_message(fmt, *args)

    def reply(self, status, payload, headers=()):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/health":
            return self.reply(200, {"status": "ok"})
        if url.path != "/order-lines":
            return self.reply(404, {"error": "not_found"})
        try:
            limit = int(query.get("limit", PAGE_SIZE))
            offset = int(base64.urlsafe_b64decode(query["cursor"]).decode().removeprefix("o:")) if "cursor" in query else 0
            since = parse_time(query["since"]) if "since" in query else None
            until = parse_time(query["until"]) if "until" in query else None
            if not 1 <= limit <= PAGE_SIZE or offset < 0:
                raise ValueError("limit or cursor out of range")
        except (ValueError, KeyError, UnicodeDecodeError):
            return self.reply(400, {"error": "bad_request"})
        key = (offset, limit, since, until)
        with self.server.lock:
            failures = self.server.failures.get(key, 0)
            fault = planned_fault(self.server.seed, offset, failures)
            self.server.failures[key] = failures + 1 if fault else 0
        if fault == 429:
            return self.reply(429, {"error": "rate_limited"}, [("Retry-After", str(self.server.retry_after))])
        if fault == 500:
            return self.reply(500, {"error": "server_error"})
        stream = with_repeat(select(self.server.versions, since, until), self.server.seed)
        page = stream[offset : offset + limit]
        more = offset + limit < len(stream)
        cursor = base64.urlsafe_b64encode(f"o:{offset + limit}".encode()).decode() if more else None
        self.reply(200, {"data": [render(self.server.seed, p) for p in page], "next_cursor": cursor})


def make_server(port=8000, seed=SEED, retry_after=1, verbose=False):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.seed, server.retry_after, server.verbose = seed, retry_after, verbose
    server.versions = load_versions(seed)
    server.failures, server.lock = {}, Lock()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--retry-after", type=int, default=1, help="seconds sent with a 429")
    parser.add_argument("--verbose", action="store_true", help="print every request")
    args = parser.parse_args()
    server = make_server(args.port, args.seed, args.retry_after, args.verbose)
    print(f"Mock API on http://127.0.0.1:{args.port} (seed {args.seed}). Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
