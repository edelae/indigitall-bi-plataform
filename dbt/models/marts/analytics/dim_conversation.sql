-- Dimension: conversation — from enriched chat conversations with dimension keys.

with conversations as (
    select * from {{ ref('int_conversations_enriched') }}
),

message_counts as (
    select
        tenant_id,
        conversation_id,
        count(*) as message_count
    from {{ ref('stg_messages') }}
    where conversation_id is not null
    group by tenant_id, conversation_id
),

close_reasons as (
    select
        tenant_id,
        conversation_id,
        close_reason,
        row_number() over (
            partition by tenant_id, conversation_id
            order by timestamp desc
        ) as rn
    from {{ ref('stg_messages') }}
    where close_reason is not null
),

-- Mejora 3: First agent/outbound message per conversation
first_agent_messages as (
    select
        tenant_id,
        conversation_id,
        min(timestamp) as first_agent_msg_at
    from {{ ref('stg_messages') }}
    where conversation_id is not null
      and direction in ('Agent', 'Outbound')
    group by tenant_id, conversation_id
),

-- Mejora 4: Average intra-conversation response time
response_pairs as (
    select
        tenant_id,
        conversation_id,
        direction,
        timestamp,
        lead(timestamp) over (
            partition by tenant_id, conversation_id
            order by timestamp
        ) as next_msg_at,
        lead(direction) over (
            partition by tenant_id, conversation_id
            order by timestamp
        ) as next_direction
    from {{ ref('stg_messages') }}
    where conversation_id is not null
      and direction in ('Inbound', 'Agent')
),

avg_response_times as (
    select
        tenant_id,
        conversation_id,
        avg(extract(epoch from next_msg_at - timestamp))::int as avg_response_time_seconds
    from response_pairs
    where direction = 'Inbound'
      and next_direction = 'Agent'
      and next_msg_at > timestamp
      and extract(epoch from next_msg_at - timestamp) < 86400
    group by tenant_id, conversation_id
),

dim_ch as (
    select channel_key, channel_code from {{ ref('dim_channel') }}
),

dim_ct as (
    select contact_key, tenant_id, contact_id from {{ ref('dim_contact') }}
    where contact_id is not null
),

dim_ag as (
    select agent_key, tenant_id, agent_id from {{ ref('dim_agent') }}
),

dim_css as (
    select conversation_session_key, tenant_id, conversation_session_id
    from {{ ref('dim_conversation_session') }}
),

final as (
    select
        row_number() over (order by c.tenant_id, c.session_id)::int as conversation_key,
        c.tenant_id,
        c.session_id as conversation_id,
        c.conversation_session_id,
        c.initial_session_id,
        ch.channel_key,
        ct.contact_key,
        ag.agent_key,
        css.conversation_session_key,
        c.queued_at,
        c.assigned_at,
        c.closed_at,
        cr.close_reason,
        c.wait_time_seconds,
        c.handle_time_seconds,
        c.total_duration_seconds,
        c.is_resolved_by_bot,
        c.is_escalated,
        coalesce(mc.message_count, 0)::int as message_count,

        -- Mejora 3: First response time (seconds from assigned to first agent message)
        case
            when c.assigned_at is not null and fam.first_agent_msg_at is not null
            then extract(epoch from fam.first_agent_msg_at - c.assigned_at)::int
        end as first_response_time_seconds,

        -- Mejora 4: Average response time within conversation
        art.avg_response_time_seconds,

        -- Mejora 5: Dead time (total duration minus handle time)
        case
            when c.total_duration_seconds is not null
                 and c.handle_time_seconds is not null
                 and c.total_duration_seconds > c.handle_time_seconds
            then c.total_duration_seconds - c.handle_time_seconds
        end as dead_time_seconds,

        -- Mejora 9: Business hours flag (8:00-17:59)
        case
            when c.queued_at is not null
            then extract(hour from c.queued_at) between 8 and 17
            else false
        end as is_business_hours

    from conversations c
    left join dim_ch ch
        on ch.channel_code = case
            when c.agent_id is not null then 'wa_callcenter'
            else 'wa_chatbot'
        end
    left join dim_ct ct
        on ct.tenant_id = c.tenant_id and ct.contact_id = c.contact_id
    left join dim_ag ag
        on ag.tenant_id = c.tenant_id and ag.agent_id = c.agent_id
    left join message_counts mc
        on mc.tenant_id = c.tenant_id and mc.conversation_id = c.session_id
    left join close_reasons cr
        on cr.tenant_id = c.tenant_id and cr.conversation_id = c.session_id and cr.rn = 1
    left join dim_css css
        on css.tenant_id = c.tenant_id
        and css.conversation_session_id = c.conversation_session_id
    left join first_agent_messages fam
        on fam.tenant_id = c.tenant_id and fam.conversation_id = c.session_id
    left join avg_response_times art
        on art.tenant_id = c.tenant_id and art.conversation_id = c.session_id
)

select * from final
