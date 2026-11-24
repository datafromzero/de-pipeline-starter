{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='order_line_id'
    )
}}

-- Grain: one row for each order line, with its product and the amount of the line.
select
    l.order_line_id,
    l.order_date,
    l.store_id,
    l.status,
    l.payment_method,
    l.units,
    p.product_name,
    p.category,
    {{ line_amount('l.units', 'p.unit_price_usd', 'l.discount_usd') }} as line_amount_usd,
    l.updated_at
from {{ ref('stg_order_lines') }} as l
join {{ ref('stg_products') }} as p using (product_id)
{% if is_incremental() %}
-- On a later run: only the lines posted since the newest one this table holds.
where l.updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
