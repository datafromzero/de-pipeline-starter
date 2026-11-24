"""Small steps that turn rows into other rows. Each one is tested on a handful of rows."""


def dedupe_latest(rows, key="order_item_id", version="updated_at"):
    """Keep one row for each key: the one with the latest version."""
    return rows.query(
        "rows",
        f"SELECT * FROM rows QUALIFY row_number() OVER (PARTITION BY {key} ORDER BY {version} DESC) = 1",
    )
