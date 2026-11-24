-- Grain: one row for each store and each day on which it sold something. Completed lines only.
select
    l.store_id,
    s.store_name,
    l.order_date,
    count(*) as lines,
    sum(l.units) as units,
    sum(l.line_amount_usd) as sales_usd
from {{ ref('int_order_lines_priced') }} as l
join {{ ref('stg_stores') }} as s using (store_id)
where l.status = 'completed'
group by l.store_id, s.store_name, l.order_date
