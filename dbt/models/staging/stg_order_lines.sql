-- Grain: one row for each order line, the latest version of it that the pipeline staged.
select
    order_item_id as order_line_id,
    order_id,
    ordered_at,
    cast(ordered_at as date) as order_date,
    store_id,
    customer_id,
    lower(status) as status,
    payment_method,
    product_id,
    quantity as units,
    discount_usd,
    updated_at
from {{ source('pipeline', 'order_lines') }}
