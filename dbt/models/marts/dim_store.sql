-- Grain: one row for each store, as it is now. A change in the file overwrites the row (type 1).
select
    md5(cast(store_id as varchar)) as store_key,
    store_id,
    store_name,
    city,
    opened_on
from {{ ref('stg_stores') }}
