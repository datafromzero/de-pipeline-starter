-- Grain: one row for each order line, with its product and the amount of the line.
select
    l.order_line_id,
    l.order_date,
    l.store_id,
    l.status,
    l.units,
    p.product_name,
    p.category,
    l.units * p.unit_price_usd - l.discount_usd as line_amount_usd
from {{ ref('stg_order_lines') }} as l
join {{ ref('stg_products') }} as p using (product_id)
