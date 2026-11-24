-- Two more orders of the 986,100 lines of DE12, to read the order of the cluster columns: the same rows, sorted by
-- date and then store, and sorted by store and then date.
CREATE OR REPLACE TABLE lines_by_date_store AS
SELECT * FROM lines_arrival ORDER BY order_date, store_id;

CREATE OR REPLACE TABLE lines_by_store_date AS
SELECT * FROM lines_arrival ORDER BY store_id, order_date;
