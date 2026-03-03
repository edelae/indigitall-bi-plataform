-- Dimension: time — 24 rows from seed data.

select
    time_key,
    hour_label,
    period_of_day,
    is_business_hour
from {{ ref('dim_time_seed') }}
