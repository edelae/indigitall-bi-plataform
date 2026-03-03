-- Intermediate: Enrich conversations with bot resolution and escalation flags.

with conversations as (
    select * from {{ ref('stg_chat_conversations') }}
),

human_agent_flags as (
    select
        tenant_id,
        conversation_id,
        bool_or(is_human) as has_human_message
    from {{ ref('stg_messages') }}
    where conversation_id is not null
    group by tenant_id, conversation_id
),

enriched as (
    select
        c.tenant_id,
        c.session_id,
        c.conversation_session_id,
        c.contact_id,
        c.agent_id,
        c.agent_email,
        c.channel,
        c.queued_at,
        c.assigned_at,
        c.closed_at,
        c.initial_session_id,
        c.wait_time_seconds,
        c.handle_time_seconds,
        c.total_duration_seconds,

        -- Bot resolution: closed without agent OR closed without human messages
        case
            when c.closed_at is not null and c.agent_id is null then true
            when c.closed_at is not null and coalesce(h.has_human_message, false) = false then true
            else false
        end as is_resolved_by_bot,

        -- Escalation: transferred to another session
        -- initial_session_id = '0' means no transfer (API default)
        case
            when c.initial_session_id is not null
                 and c.initial_session_id <> '0'
                 and c.initial_session_id <> ''
                 and c.initial_session_id <> c.session_id then true
            else false
        end as is_escalated,

        -- Event date for date_key lookup
        coalesce(c.closed_at, c.assigned_at, c.queued_at)::date as event_date

    from conversations c
    left join human_agent_flags h
        on h.tenant_id = c.tenant_id and h.conversation_id = c.session_id
)

select * from enriched
