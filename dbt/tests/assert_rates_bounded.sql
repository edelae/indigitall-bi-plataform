-- Test: rate columns (ctr, tasa_entrega, open_rate, conversion_rate)
-- must be between 0.0 and 100.0.
-- Returns rows that violate the constraint (test passes when 0 rows returned).

select
    tenant_id,
    date,
    canal,
    'ctr' as rate_name,
    ctr as value
from {{ source('raw', 'toques_daily') }}
where ctr < 0 or ctr > 100

union all

select
    tenant_id,
    date,
    canal,
    'tasa_entrega' as rate_name,
    tasa_entrega as value
from {{ source('raw', 'toques_daily') }}
where tasa_entrega < 0 or tasa_entrega > 100

union all

select
    tenant_id,
    date,
    canal,
    'open_rate' as rate_name,
    open_rate as value
from {{ source('raw', 'toques_daily') }}
where open_rate < 0 or open_rate > 100

union all

select
    tenant_id,
    date,
    canal,
    'conversion_rate' as rate_name,
    conversion_rate as value
from {{ source('raw', 'toques_daily') }}
where conversion_rate < 0 or conversion_rate > 100
