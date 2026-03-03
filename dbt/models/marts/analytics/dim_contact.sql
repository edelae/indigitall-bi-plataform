-- Dimension: contact — WhatsApp contacts only (API SMS has no phone).

with unified as (
    select * from {{ ref('int_dim_contact_unified') }}
),

conversation_counts as (
    select
        tenant_id,
        contact_id,
        count(distinct session_id)::int as total_conversations
    from {{ ref('int_conversations_enriched') }}
    where contact_id is not null
    group by tenant_id, contact_id
),

numbered as (
    select
        row_number() over (order by u.tenant_id, u.contact_id)::int as contact_key,
        u.tenant_id,
        u.contact_id,
        u.contact_name,
        u.first_seen_date,
        u.last_seen_date,
        coalesce(u.total_events, 0)::int as total_events,
        true as is_active,
        coalesce(cc.total_conversations, 0)::int as total_conversations,
        coalesce(cc.total_conversations, 0) > 0 as has_conversations
    from unified u
    left join conversation_counts cc
        on cc.tenant_id = u.tenant_id and cc.contact_id = u.contact_id
)

select * from numbered
