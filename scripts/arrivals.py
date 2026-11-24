"""How often orders arrive, from the file behind the mock API. Run it with: uv run python scripts/arrivals.py"""

import duckdb

ORDERS = "mock_api_data/orders.csv"


def one(sql):
    return duckdb.sql(sql).fetchall()[0]


days, orders = one(f"SELECT count(DISTINCT ordered_at::DATE), count(*) FROM '{ORDERS}'")
per_day = f"SELECT ordered_at::DATE AS day, count(*) AS n FROM '{ORDERS}' GROUP BY day"
per_hour = f"SELECT date_trunc('hour', ordered_at) AS hour, count(*) AS n FROM '{ORDERS}' GROUP BY hour"
print(f"{orders:,} orders on {days} days")
print(f"per day: fewest {one(f'SELECT min(n) FROM ({per_day})')[0]}, median {one(f'SELECT median(n) FROM ({per_day})')[0]}, most {one(f'SELECT max(n) FROM ({per_day})')[0]}")
print(f"most orders in one hour: {one(f'SELECT max(n) FROM ({per_hour})')[0]}")
