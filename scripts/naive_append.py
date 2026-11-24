"""What a plain INSERT does with lines that are already loaded. Run it after the loads of lesson DE4."""

import duckdb

from pipeline.config import RAW_DIR
from pipeline.ingest import window_name
from pipeline.load import connect
from pipeline.stage import staged_lines

con = connect()
pages = RAW_DIR / "order_lines" / window_name(None, None) / "page-*.json"
staged_lines(con, str(pages)).create_view("everything", replace=True)
before = con.execute("SELECT count(*) FROM order_lines").fetchall()[0][0]
try:
    con.execute("INSERT INTO order_lines SELECT * FROM everything")
except duckdb.ConstraintException as error:
    print(f"refused: {str(error).splitlines()[0]}")
after = con.execute("SELECT count(*) FROM order_lines").fetchall()[0][0]
print(f"rows before {before}, after {after}")
