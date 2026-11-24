-- A store cannot sell before the day it opened. The test passes when this returns no rows.
select
    f.store_id,
    f.order_date,
    s.opened_on
from {{ ref('fct_store_daily_sales') }} as f
join {{ ref('stg_stores') }} as s using (store_id)
where f.order_date < s.opened_on
