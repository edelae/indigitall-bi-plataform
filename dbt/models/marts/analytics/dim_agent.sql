-- Dimension: agent — from staged agents enriched with conversation dates and email.

with agents as (
    select * from {{ ref('stg_agents') }}
),

conversation_dates as (
    select
        tenant_id,
        agent_id,
        min(queued_at::date) as first_active,
        max(coalesce(closed_at, assigned_at, queued_at)::date) as last_active
    from {{ ref('stg_chat_conversations') }}
    where agent_id is not null
    group by tenant_id, agent_id
),

agent_emails as (
    select distinct on (tenant_id, agent_id)
        tenant_id,
        agent_id,
        agent_email
    from {{ ref('stg_chat_conversations') }}
    where agent_id is not null and agent_email is not null
    order by tenant_id, agent_id, closed_at desc nulls last
),

enriched as (
    select
        row_number() over (order by a.tenant_id, a.agent_id)::int as agent_key,
        a.tenant_id,
        a.agent_id,
        ae.agent_email,
        true as is_active,
        cd.first_active,
        cd.last_active
    from agents a
    left join conversation_dates cd
        on a.tenant_id = cd.tenant_id and a.agent_id = cd.agent_id
    left join agent_emails ae
        on a.tenant_id = ae.tenant_id and a.agent_id = ae.agent_id
)

select * from enriched
