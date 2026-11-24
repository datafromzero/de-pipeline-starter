-- The physical tables of the cafe: three tables that point at each other, and the table of one grain.
DROP TABLE IF EXISTS store_daily_sales;
DROP TABLE IF EXISTS order_lines;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    store_id INTEGER PRIMARY KEY,
    store_name VARCHAR NOT NULL UNIQUE,
    city VARCHAR NOT NULL,
    opened_on DATE NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR NOT NULL UNIQUE,
    category VARCHAR NOT NULL CHECK (category IN ('coffee', 'tea', 'bakery', 'food')),
    unit_price_usd DECIMAL(6, 2) NOT NULL CHECK (unit_price_usd > 0)
);

CREATE TABLE order_lines (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    ordered_at TIMESTAMP NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores (store_id),
    customer_id INTEGER,
    status VARCHAR NOT NULL CHECK (status IN ('completed', 'canceled')),
    payment_method VARCHAR NOT NULL CHECK (payment_method IN ('card', 'mobile', 'cash')),
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    discount_usd DECIMAL(8, 2) NOT NULL CHECK (discount_usd >= 0),
    updated_at TIMESTAMP NOT NULL,
    channel VARCHAR CHECK (channel IN ('counter', 'app'))
);

-- One row for each store and day: the key is the grain.
CREATE TABLE store_daily_sales (
    store_id INTEGER NOT NULL REFERENCES stores (store_id),
    order_date DATE NOT NULL,
    lines INTEGER NOT NULL,
    units INTEGER NOT NULL,
    PRIMARY KEY (store_id, order_date)
);

INSERT INTO stores SELECT * FROM 'data/staging/stores.parquet';
INSERT INTO products SELECT * FROM 'data/staging/products.parquet';
INSERT INTO order_lines SELECT * FROM 'data/staging/order_lines.parquet';
INSERT INTO store_daily_sales
SELECT store_id, CAST(ordered_at AS DATE), count(*), sum(quantity)
FROM order_lines
WHERE status = 'completed'
GROUP BY store_id, CAST(ordered_at AS DATE);
