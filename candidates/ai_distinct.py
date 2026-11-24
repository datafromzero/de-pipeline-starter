"""Written for the lesson, in the style of an assistant's answer. Not produced by a model."""


def dedupe_latest(rows, key="order_item_id", version="updated_at"):
    """Remove duplicate rows."""
    return rows.distinct()
