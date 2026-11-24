"""Write the partner's product file as it was at version 1, 2 or 3, to data/partner/products.parquet.

    uv run python scripts/partner_files.py 2

The history is invented for the lesson: the real products.csv never changes. Version 1 is products.csv with an
updated_at of 2026-01-01 on every row. Version 2 moves product 11 (Blueberry Muffin) from bakery to food on 2026-04-15, and
version 3 also moves product 14 (Avocado Toast) from food to bakery on 2026-05-20. Each version replaces the file, as a
partner's new export would.
"""

import sys

import duckdb

from pipeline.config import DATA_DIR, SOURCE_FILES

CHANGES = {  # version: (product_id, new category, updated_at); a version keeps the changes of the versions before it
    2: (11, "food", "2026-04-15 12:00:00"),
    3: (14, "bakery", "2026-05-20 09:30:00"),
}


def main(version):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE products AS SELECT *, TIMESTAMP '2026-01-01 00:00:00' AS updated_at "
        f"FROM read_csv('{SOURCE_FILES / 'products.csv'}', types = {{'product_id': 'INTEGER', 'unit_price_usd': 'DECIMAL(6, 2)'}})"
    )
    for number in range(2, version + 1):
        product_id, category, updated_at = CHANGES[number]
        con.execute(
            "UPDATE products SET category = ?, updated_at = ?::TIMESTAMP WHERE product_id = ?",
            [category, updated_at, product_id],
        )
    folder = DATA_DIR / "partner"
    folder.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY (SELECT * FROM products ORDER BY product_id) TO '{folder / 'products.parquet'}' (FORMAT parquet)")
    changed = con.execute("SELECT count(*) FROM products WHERE updated_at > TIMESTAMP '2026-01-01'").fetchall()[0][0]
    print(f"data/partner/products.parquet: version {version}, 16 products, {changed} changed since version 1")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"1", "2", "3"}:
        sys.exit(__doc__)
    main(int(sys.argv[1]))
