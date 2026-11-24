-- Two copies of one invented table of 986,100 lines: the 3,287 real lines copied 300 times, copy k dated k days later.
-- lines_arrival keeps the lines in a shuffled order, as if they came in from many tills; lines_by_date sorts the same rows.
CREATE OR REPLACE TABLE lines_arrival AS
SELECT
    order_item_id + 10000 * k AS order_item_id,
    store_id,
    status,
    quantity,
    CAST(ordered_at AS DATE) + CAST(k AS INTEGER) AS order_date
FROM order_lines, range(300) AS copies(k)
ORDER BY hash(order_item_id + 10000 * k);

CREATE OR REPLACE TABLE lines_by_date AS
SELECT * FROM lines_arrival ORDER BY order_date, store_id;
