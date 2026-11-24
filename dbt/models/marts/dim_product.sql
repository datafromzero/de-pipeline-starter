-- Grain: one row for each version of a product. A change in the partner's file adds a row (type 2).
select
    dbt_scd_id as product_key,
    product_id,
    product_name,
    category,
    unit_price_usd,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current
from {{ ref('products_snapshot') }}
