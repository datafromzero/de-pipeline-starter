-- Every staged line must be in the fact. A row here is the count on both sides when they differ.
select
    s.staged_lines,
    f.fact_lines
from (select count(*) as staged_lines from {{ ref('stg_order_lines') }}) as s
cross join (select count(*) as fact_lines from {{ ref('fct_order_lines') }}) as f
where s.staged_lines <> f.fact_lines
