{% set statuses = ['completed', 'canceled'] %}
-- Grain: one row for each store. One column of net amount for each status in the list above.
select
    store_id,
{% for status_name in statuses %}
    sum(line_amount_usd) filter (where status = '{{ status_name }}') as {{ status_name }}_usd{{ "," if not loop.last }}
{% endfor %}
from {{ ref('int_order_lines_priced') }}
group by store_id
