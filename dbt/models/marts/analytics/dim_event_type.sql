-- Dimension: event_type — 18 event types from seed data.

select
    event_type_key,
    event_code,
    event_name,
    event_category,
    is_terminal,
    ordinal
from {{ ref('dim_event_type_seed') }}
