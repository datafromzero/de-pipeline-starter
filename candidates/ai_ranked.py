"""Written for the lesson, in the style of an assistant's answer. Not produced by a model."""


def dedupe_latest(rows, key="order_item_id", version="updated_at"):
    """Keep the latest version of each key."""
    ranked = rows.project(f"*, row_number() OVER (PARTITION BY {key} ORDER BY {version} DESC) AS rank_in_key")
    return ranked.filter("rank_in_key = 1").project("* EXCLUDE (rank_in_key)")
