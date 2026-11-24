-- Every completed line of staging must be in the mart. A row here is the count on both sides when they differ.
select
    s.completed_lines,
    m.mart_lines
from (select count(*) as completed_lines from {{ ref('stg_order_lines') }} where status = 'completed') as s
cross join (select sum(lines) as mart_lines from {{ ref('fct_store_daily_sales') }}) as m
where s.completed_lines <> m.mart_lines
