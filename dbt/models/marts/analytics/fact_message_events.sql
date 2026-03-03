-- Fact: message_events — unified event-level grain from all channels.
-- One row = one atomic event (sent, delivered, read, clicked, failed, etc.).
--
-- Sources:
--   messages (122K)          → 1 fact row per message
--   sms_envios (578K)        → 1 fact row per SMS (sent only, API has no delivery/clicks)
--   toques_daily (288)       → up to 9 fact rows per toques row (aggregated)
--   chat_conversations (38K) → 1-3 lifecycle events per conversation

-- ═══════════════════════════════════════════
-- Dimension lookups
-- ═══════════════════════════════════════════

with dim_tn as (
    select tenant_key, tenant_id from {{ ref('dim_tenant') }}
),

dim_ch as (
    select channel_key, channel_code from {{ ref('dim_channel') }}
),

dim_et as (
    select event_type_key, event_code from {{ ref('dim_event_type') }}
),

dim_ct_by_cid as (
    select contact_key, tenant_id, contact_id
    from {{ ref('dim_contact') }}
    where contact_id is not null
),

dim_ag as (
    select agent_key, tenant_id, agent_id from {{ ref('dim_agent') }}
),

dim_cp as (
    select campaign_key, tenant_id, campaign_id from {{ ref('dim_campaign') }}
),

dim_cv as (
    select conversation_key, tenant_id, conversation_id, conversation_session_key
    from {{ ref('dim_conversation') }}
),

-- ═══════════════════════════════════════════
-- Source 1: WhatsApp messages → 1 event per message
-- ═══════════════════════════════════════════

messages_events as (
    select
        m.tenant_id,
        m.date as event_date,
        m.hour as event_hour,
        m.channel_code,
        m.event_code,
        m.message_id as source_message_id,
        'messages'::varchar(30) as source_table,
        1 as event_count,
        m.content_type,
        m.send_type,
        case
            when m.direction = 'Inbound' then 'Inbound'
            when m.direction = 'Bot' then 'Bot'
            when m.direction = 'Agent' then 'Agent'
            when m.direction = 'Outbound' then 'Outbound'
            else 'System'
        end as direction,
        m.intent,
        m.is_fallback,
        m.is_bot,
        m.is_human,
        m.wait_time_seconds as response_time_seconds,
        m.contact_id,
        m.agent_id,
        null::varchar(100) as campaign_id,
        m.conversation_id,
        null::int as total_chunks,
        null::boolean as is_flash,
        m.status as status_detail
    from {{ ref('int_messages_classified') }} m
),

-- ═══════════════════════════════════════════
-- Source 2: SMS events → 1 sent event per SMS (API-only)
-- ═══════════════════════════════════════════

sms_events as (
    select
        s.tenant_id,
        s.event_date,
        s.event_hour as event_hour,
        s.channel_code,
        s.event_code,
        s.source_message_id,
        s.source_table,
        s.event_count,
        null::varchar(30) as content_type,
        s.send_type,
        'Outbound'::varchar(20) as direction,
        null::varchar(200) as intent,
        null::boolean as is_fallback,
        null::boolean as is_bot,
        null::boolean as is_human,
        null::int as response_time_seconds,
        null::varchar(100) as contact_id,
        null::varchar(100) as agent_id,
        s.campaign_id,
        null::varchar(100) as conversation_id,
        s.total_chunks,
        s.is_flash,
        null::varchar(50) as status_detail
    from {{ ref('int_sms_events_unpivoted') }} s
),

-- ═══════════════════════════════════════════
-- Source 3: Toques daily → aggregated events
-- ═══════════════════════════════════════════

toques_events as (
    select
        t.tenant_id,
        t.event_date,
        null::smallint as event_hour,
        t.channel_code,
        t.event_code,
        null::varchar(100) as source_message_id,
        t.source_table,
        t.event_count,
        null::varchar(30) as content_type,
        null::varchar(30) as send_type,
        'Outbound'::varchar(20) as direction,
        null::varchar(200) as intent,
        null::boolean as is_fallback,
        null::boolean as is_bot,
        null::boolean as is_human,
        null::int as response_time_seconds,
        null::varchar(100) as contact_id,
        null::varchar(100) as agent_id,
        null::varchar(100) as campaign_id,
        null::varchar(100) as conversation_id,
        null::int as total_chunks,
        null::boolean as is_flash,
        null::varchar(50) as status_detail
    from {{ ref('int_toques_events_unpivoted') }} t
),

-- ═══════════════════════════════════════════
-- Source 4: Conversations → lifecycle events
-- ═══════════════════════════════════════════

conversation_queued as (
    select
        tenant_id,
        queued_at::date as event_date,
        extract(hour from queued_at)::smallint as event_hour,
        case when agent_id is not null then 'wa_callcenter' else 'wa_chatbot' end as channel_code,
        'queued' as event_code,
        session_id as source_message_id,
        'chat_conversations'::varchar(30) as source_table,
        1 as event_count,
        null::varchar(30) as content_type,
        null::varchar(30) as send_type,
        'System'::varchar(20) as direction,
        null::varchar(200) as intent,
        null::boolean as is_fallback,
        null::boolean as is_bot,
        null::boolean as is_human,
        null::int as response_time_seconds,
        contact_id,
        agent_id,
        null::varchar(100) as campaign_id,
        session_id as conversation_id,
        null::int as total_chunks,
        null::boolean as is_flash,
        null::varchar(50) as status_detail
    from {{ ref('int_conversations_enriched') }}
    where queued_at is not null
),

conversation_assigned as (
    select
        tenant_id,
        assigned_at::date as event_date,
        extract(hour from assigned_at)::smallint as event_hour,
        'wa_callcenter' as channel_code,
        'assigned' as event_code,
        session_id as source_message_id,
        'chat_conversations'::varchar(30) as source_table,
        1 as event_count,
        null::varchar(30) as content_type,
        null::varchar(30) as send_type,
        'System'::varchar(20) as direction,
        null::varchar(200) as intent,
        null::boolean as is_fallback,
        null::boolean as is_bot,
        null::boolean as is_human,
        wait_time_seconds as response_time_seconds,
        contact_id,
        agent_id,
        null::varchar(100) as campaign_id,
        session_id as conversation_id,
        null::int as total_chunks,
        null::boolean as is_flash,
        null::varchar(50) as status_detail
    from {{ ref('int_conversations_enriched') }}
    where assigned_at is not null and agent_id is not null
),

conversation_closed as (
    select
        tenant_id,
        closed_at::date as event_date,
        extract(hour from closed_at)::smallint as event_hour,
        case when agent_id is not null then 'wa_callcenter' else 'wa_chatbot' end as channel_code,
        'closed' as event_code,
        session_id as source_message_id,
        'chat_conversations'::varchar(30) as source_table,
        1 as event_count,
        null::varchar(30) as content_type,
        null::varchar(30) as send_type,
        'System'::varchar(20) as direction,
        null::varchar(200) as intent,
        null::boolean as is_fallback,
        null::boolean as is_bot,
        null::boolean as is_human,
        handle_time_seconds as response_time_seconds,
        contact_id,
        agent_id,
        null::varchar(100) as campaign_id,
        session_id as conversation_id,
        null::int as total_chunks,
        null::boolean as is_flash,
        null::varchar(50) as status_detail
    from {{ ref('int_conversations_enriched') }}
    where closed_at is not null
),

-- ═══════════════════════════════════════════
-- UNION ALL sources
-- ═══════════════════════════════════════════

all_events as (
    select * from messages_events
    union all
    select * from sms_events
    union all
    select * from toques_events
    union all
    select * from conversation_queued
    union all
    select * from conversation_assigned
    union all
    select * from conversation_closed
),

-- ═══════════════════════════════════════════
-- Resolve dimension keys
-- ═══════════════════════════════════════════

with_keys as (
    select
        -- Dimension FKs
        tn.tenant_key,
        to_char(e.event_date, 'YYYYMMDD')::int as date_key,
        e.event_hour as time_key,
        ch.channel_key,
        et.event_type_key,
        ct_cid.contact_key,
        ag.agent_key,
        cp.campaign_key,
        cv.conversation_key,
        cv.conversation_session_key,

        -- Degenerate dimensions
        e.source_message_id,
        e.source_table,

        -- Measures
        e.event_count,

        -- Context
        e.content_type,
        e.send_type,
        e.direction,
        e.intent,
        e.is_fallback,
        e.is_bot,
        e.is_human,
        e.response_time_seconds,
        e.total_chunks,
        e.is_flash,
        e.status_detail

    from all_events e
    left join dim_tn tn on tn.tenant_id = e.tenant_id
    left join dim_ch ch on ch.channel_code = e.channel_code
    left join dim_et et on et.event_code = e.event_code
    left join dim_ct_by_cid ct_cid
        on ct_cid.tenant_id = e.tenant_id
        and e.contact_id is not null
        and ct_cid.contact_id = e.contact_id
    left join dim_ag ag
        on ag.tenant_id = e.tenant_id and ag.agent_id = e.agent_id
    left join dim_cp cp
        on cp.tenant_id = e.tenant_id and cp.campaign_id = e.campaign_id
    left join dim_cv cv
        on cv.tenant_id = e.tenant_id and cv.conversation_id = e.conversation_id
    where e.event_date is not null
)

select * from with_keys
