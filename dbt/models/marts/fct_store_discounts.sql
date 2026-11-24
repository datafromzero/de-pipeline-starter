-- Grain: one row for each store. The list amount, the discounts and the net amount of the completed lines.
select
    l.store_id,
    sum(l.units * p.unit_price_usd) as list_usd,
    sum(l.discount_usd) as discount_usd,
    sum({{ line_amount('l.units', 'p.unit_price_usd', 'l.discount_usd') }}) as net_usd
from {{ ref('stg_order_lines') }} as l
join {{ ref('stg_products') }} as p using (product_id)
where l.status = 'completed'
group by l.store_id
