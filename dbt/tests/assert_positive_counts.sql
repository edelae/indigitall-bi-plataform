-- Test: no negative counts in toques_daily stats columns.
-- Returns rows that violate the constraint (test passes when 0 rows returned).

select
    tenant_id,
    date,
    canal,
    'enviados' as field,
    enviados as value
from {{ source('raw', 'toques_daily') }}
where enviados < 0

union all

select
    tenant_id,
    date,
    canal,
    'entregados' as field,
    entregados as value
from {{ source('raw', 'toques_daily') }}
where entregados < 0

union all

select
    tenant_id,
    date,
    canal,
    'clicks' as field,
    clicks as value
from {{ source('raw', 'toques_daily') }}
where clicks < 0
