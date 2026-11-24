"""The first page of the API, summed two ways. Run it with: uv run python scripts/tour.py"""

import json
from urllib.request import urlopen

import duckdb

from pipeline.config import API_URL, RAW_DIR

with urlopen(f"{API_URL}/order-lines?limit=100", timeout=10) as response:
    body = response.read()

# ETL: transform in Python, keep only the result.
rows = [(line["order_item_id"], line["quantity"]) for line in json.loads(body)["data"]]
print(f"ETL: {sum(quantity for _, quantity in rows)} units on {len(rows)} lines; raw bytes kept: none")

# ELT: land the bytes first, then transform with SQL where the data now lives.
page = RAW_DIR / "tour" / "page-0001.json"
page.parent.mkdir(parents=True, exist_ok=True)
page.write_bytes(body)
units = duckdb.sql(f"SELECT sum(line.quantity) FROM (SELECT unnest(data) AS line FROM read_json('{page}'))").fetchall()[0][0]
print(f"ELT: {units} units; raw bytes kept: {page.stat().st_size:,} in data/raw/tour/page-0001.json")
