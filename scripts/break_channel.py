"""Write data/broken/channel_gone.parquet: the staged lines, with no channel on the lines updated from June 15.

Run it with: uv run python scripts/break_channel.py
"""

import duckdb

duckdb.sql("""
    COPY (
        SELECT * REPLACE (CASE WHEN updated_at >= TIMESTAMP '2026-06-15' THEN NULL ELSE channel END AS channel)
        FROM read_parquet('data/staging/order_lines.parquet')
    ) TO 'data/broken/channel_gone.parquet' (FORMAT parquet)
""")
