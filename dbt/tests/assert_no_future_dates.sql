-- Test: no dates in toques_daily or daily_stats should be in the future.
-- Returns rows that violate the constraint (test passes when 0 rows returned).

select 'toques_daily' as source_table, date
from {{ source('raw', 'toques_daily') }}
where date > current_date

union all

select 'daily_stats' as source_table, date
from {{ source('raw', 'daily_stats') }}
where date > current_date
