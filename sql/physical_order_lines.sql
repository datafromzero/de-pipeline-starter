-- The contract of DE6 as a table: a row that breaks a rule is refused.
CREATE OR REPLACE TABLE order_lines (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    ordered_at TIMESTAMP NOT NULL,
    store_id INTEGER NOT NULL,
    customer_id INTEGER,
    status VARCHAR NOT NULL CHECK (status IN ('completed', 'canceled')),
    payment_method VARCHAR NOT NULL CHECK (payment_method IN ('card', 'mobile', 'cash')),
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    discount_usd DECIMAL(8, 2) NOT NULL CHECK (discount_usd >= 0),
    updated_at TIMESTAMP NOT NULL,
    channel VARCHAR CHECK (channel IN ('counter', 'app'))
);
