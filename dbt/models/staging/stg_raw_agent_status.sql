-- Staging: flatten raw_chat_stats (agent/status) → agent count snapshot.
-- Source: raw.raw_chat_stats (endpoint like '%/agent/status%')
-- Target: public.agents — MINIMAL: only activeAgents count, no individual agent IDs.
-- NOTE: Full agent data requires JWT auth which is not currently available.

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_chat_stats') }}
    where endpoint like '%/agent/status%'
      and source_data->'data' is not null
),

extracted as (
    select
        tenant_id,
        coalesce((source_data->'data'->>'activeAgents')::int, 0) as active_agents,
        loaded_at
    from raw_rows
),

latest as (
    select *,
        row_number() over (
            partition by tenant_id
            order by loaded_at desc
        ) as _rn
    from extracted
)

select
    tenant_id,
    active_agents,
    loaded_at as snapshot_at
from latest
where _rn = 1
