-- Grain: one row for each product on the menu.
select
    product_id,
    product_name,
    category,
    unit_price_usd
from {{ source('pipeline', 'products') }}
