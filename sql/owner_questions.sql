-- Three questions of the owner, answered from the star. Run against data/serving/analytics.duckdb.

-- 1. Net sales of the completed lines of each store.
SELECT s.store_name, count(*) AS lines, sum(f.line_amount_usd) AS net_sales_usd
FROM fct_order_lines AS f
JOIN dim_store AS s USING (store_key)
WHERE f.status = 'completed'
GROUP BY s.store_name
ORDER BY s.store_name;

-- 2. Net sales of each category, with the category a product had when the line was ordered.
SELECT p.category, count(*) AS lines, sum(f.line_amount_usd) AS net_sales_usd
FROM fct_order_lines AS f
JOIN dim_product AS p USING (product_key)
WHERE f.status = 'completed'
GROUP BY p.category
ORDER BY p.category;

-- 3. Do the star and the store-day table agree with the staged lines?
SELECT
    (SELECT count(*) FROM 'data/staging/order_lines.parquet' WHERE lower(status) = 'completed') AS staged_lines,
    (SELECT count(*) FROM fct_order_lines WHERE status = 'completed') AS fact_lines,
    (SELECT sum(lines) FROM fct_store_daily_sales) AS mart_lines,
    (SELECT sum(line_amount_usd) FROM fct_order_lines WHERE status = 'completed') AS fact_net_usd,
    (SELECT sum(sales_usd) FROM fct_store_daily_sales) AS mart_net_usd;
