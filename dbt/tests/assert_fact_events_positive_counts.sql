-- Validate that event_count is always positive in fact_message_events.

select
    source_table,
    event_count,
    date_key
from {{ ref('fact_message_events') }}
where event_count <= 0
limit 10
