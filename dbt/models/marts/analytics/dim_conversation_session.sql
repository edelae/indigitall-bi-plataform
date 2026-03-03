-- Dimension: conversation_session — logical conversation level.
-- Groups agent sessions by conversation_session_id with contact reasons.

with sessions as (
    select * from {{ ref('int_conversation_sessions') }}
),

dim_tn as (
    select tenant_key, tenant_id from {{ ref('dim_tenant') }}
),

dim_ct as (
    select contact_key, tenant_id, contact_id
    from {{ ref('dim_contact') }}
    where contact_id is not null
),

dim_cr as (
    select contact_reason_key, reason_code
    from {{ ref('dim_contact_reason') }}
),

final as (
    select
        row_number() over (
            order by s.tenant_id, s.conversation_session_id
        )::int as conversation_session_key,
        s.tenant_id,
        s.conversation_session_id,
        tn.tenant_key,
        ct.contact_key,
        s.first_queued_at,
        s.last_closed_at,
        s.total_duration_seconds,
        s.agent_session_count,
        s.total_wait_seconds,
        s.total_handle_seconds,
        s.last_close_reason,
        s.dominant_intent,
        s.contact_reason_l1_key,
        s.contact_reason_l2_key,
        s.classification_method,
        s.is_classified
    from sessions s
    left join dim_tn tn on tn.tenant_id = s.tenant_id
    left join dim_ct ct
        on ct.tenant_id = s.tenant_id and ct.contact_id = s.contact_id
)

select * from final
