-- Intermediate: SMS sent events (API provides no delivery status or clicks).
-- 1 SMS = 1 fact row: sent only.

with sms as (
    select * from {{ ref('stg_sms_envios') }}
)

select
    tenant_id,
    sending_id as source_message_id,
    'sms' as channel_code,
    'sent' as event_code,
    sent_date as event_date,
    sent_hour as event_hour,
    campaign_id,
    1 as event_count,
    sending_type as send_type,
    total_chunks,
    is_flash,
    'sms_envios'::varchar(30) as source_table
from sms
