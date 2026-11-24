-- Grain: one row for each store.
select
    store_id,
    store_name,
    city,
    opened_on
from {{ source('pipeline', 'stores') }}
