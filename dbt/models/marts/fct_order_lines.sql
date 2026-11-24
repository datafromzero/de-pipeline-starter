-- Grain: one row for each order line. It holds the keys of the dimension rows that were true when the line was ordered.
select
    l.order_line_id,
    p.product_key,
    s.store_key,
    l.order_date,
    l.status,
    l.units,
    l.discount_usd,
    {{ line_amount('l.units', 'p.unit_price_usd', 'l.discount_usd') }} as line_amount_usd
from {{ ref('stg_order_lines') }} as l
join {{ ref('dim_product') }} as p
    on l.product_id = p.product_id
    and l.ordered_at >= p.valid_from
    and l.ordered_at < coalesce(p.valid_to, timestamp '9999-12-31')
join {{ ref('dim_store') }} as s using (store_id)
