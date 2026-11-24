"""List the quarantined lines and the version of each that the table holds now. Run it with: uv run python scripts/quarantined.py"""

import duckdb

from pipeline.config import SERVING_DIR

con = duckdb.connect(str(SERVING_DIR / "cafe.duckdb"), read_only=True)
print(con.sql("""
    SELECT q.check_name, q.order_item_id, q.updated_at AS held_version, l.updated_at AS table_version, l.quantity AS table_quantity
    FROM quarantine q LEFT JOIN order_lines l USING (order_item_id)
    ORDER BY q.order_item_id
"""))
