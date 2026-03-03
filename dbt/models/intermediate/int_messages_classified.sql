-- Intermediate: Classify messages with channel_code and event_code.

with messages as (
    select * from {{ ref('stg_messages') }}
),

classified as (
    select
        tenant_id,
        message_id,
        timestamp,
        date,
        hour,
        send_type,
        direction,
        content_type,
        status,
        contact_name,
        contact_id,
        conversation_id,
        agent_id,
        intent,
        is_fallback,
        is_bot,
        is_human,
        wait_time_seconds,
        handle_time_seconds,

        -- Channel classification
        case
            when is_bot then 'wa_chatbot'
            when is_human or agent_id is not null then 'wa_callcenter'
            else 'wa_marketing'
        end as channel_code,

        -- Event type derived from status
        case
            when lower(status) = 'channel_sent' then 'sent'
            when lower(status) = 'channel_delivered' then 'delivered'
            when lower(status) = 'channel_read' then 'read'
            when lower(status) in ('sent') then 'sent'
            when lower(status) in ('delivered') then 'delivered'
            when lower(status) in ('read') then 'read'
            when lower(status) like '%fail%' or lower(status) like '%error%' then 'failed'
            else 'sent'
        end as event_code

    from messages
)

select * from classified
