-- Validate that fact_message_events has no orphan dimension keys.
-- All non-null FKs must resolve to an existing dimension row.

with fact as (
    select * from {{ ref('fact_message_events') }}
),

orphan_channels as (
    select 'channel_key' as fk_name, channel_key as fk_value
    from fact f
    where f.channel_key is not null
      and not exists (
          select 1 from {{ ref('dim_channel') }} d where d.channel_key = f.channel_key
      )
    limit 5
),

orphan_event_types as (
    select 'event_type_key' as fk_name, event_type_key as fk_value
    from fact f
    where f.event_type_key is not null
      and not exists (
          select 1 from {{ ref('dim_event_type') }} d where d.event_type_key = f.event_type_key
      )
    limit 5
),

orphan_tenants as (
    select 'tenant_key' as fk_name, tenant_key as fk_value
    from fact f
    where f.tenant_key is not null
      and not exists (
          select 1 from {{ ref('dim_tenant') }} d where d.tenant_key = f.tenant_key
      )
    limit 5
)

select * from orphan_channels
union all
select * from orphan_event_types
union all
select * from orphan_tenants
