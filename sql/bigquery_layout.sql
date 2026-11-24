-- BigQuery, for the free sandbox. Not run: no account was used.
-- The shapes follow the Google Cloud pages named in the lesson. Load lines_arrival.parquet first (see the lesson), then:
CREATE TABLE cafe.lines
PARTITION BY DATE_TRUNC(order_date, MONTH)
CLUSTER BY store_id
AS (SELECT * FROM cafe.lines_arrival);
