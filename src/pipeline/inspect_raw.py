"""Read the landed pages and say what is in them, without changing anything.

Run it with one word: keys, fields or fingerprint.
"""

import hashlib
import json
import sys
from collections import Counter

from pipeline.config import RAW_DIR
from pipeline.ingest import window_name

CONTRACT = {
    "order_item_id", "order_id", "ordered_at", "store_id", "customer_id", "status",
    "payment_method", "product_id", "quantity", "discount_usd", "updated_at",
}


def records_by_page(folder):
    """Yield (page file name, records) for every landed page, in order."""
    for page in sorted(folder.glob("page-*.json")):
        yield page.name, json.loads(page.read_text())["data"]


def keys(folder):
    """How many records came, how many distinct lines they make, and which keys came twice."""
    counts = Counter(r["order_item_id"] for _, records in records_by_page(folder) for r in records)
    print(f"records: {sum(counts.values())}")
    print(f"distinct order_item_id: {len(counts)}")
    print(f"repeated keys: {[key for key, n in counts.items() if n > 1]}")


def fields(folder):
    """Name every field that the contract does not list, and the page where it first appears."""
    first_seen = {}
    for name, records in records_by_page(folder):
        for record in records:
            for field in set(record) - CONTRACT:
                first_seen.setdefault(field, name)
    for field, name in first_seen.items():
        print(f"field outside the contract: {field} (first seen in {name})")
    if not first_seen:
        print("no field outside the contract")


def fingerprint(folder):
    """One short code for the bytes of all pages: equal codes mean equal pages."""
    pages = sorted(folder.glob("page-*.json"))
    code = hashlib.sha256(b"".join(page.read_bytes() for page in pages)).hexdigest()[:12]
    print(f"{len(pages)} pages, fingerprint {code}")


if __name__ == "__main__":
    report = {"keys": keys, "fields": fields, "fingerprint": fingerprint}[sys.argv[1]]
    report(RAW_DIR / "order_lines" / window_name(None, None))
