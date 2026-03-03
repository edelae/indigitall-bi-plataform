-- Dimension: channel — 9 channel types from seed data.

select
    channel_key,
    channel_code,
    channel_name,
    sub_channel,
    channel_family,
    is_bidirectional,
    icon_class,
    display_order
from {{ ref('dim_channel_seed') }}
