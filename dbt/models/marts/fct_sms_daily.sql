-- Mart: fct_sms_daily — daily SMS metrics combining envios + API stats.
-- Prioritizes sms_daily_stats (API aggregate) for totals,
-- falls back to sms_envios aggregation.

{{ config(
    schema='public_marts',
    materialized='table',
) }}

with api_stats as (
    select
        tenant_id,
        date,
        total_sent,
        total_delivered,
        total_rejected,
        total_chunks,
        total_clicks,
        unique_contacts,
        total_cost,
        delivery_rate,
        ctr
    from {{ ref('stg_sms_daily_stats') }}
),

envio_stats as (
    select
        tenant_id,
        sent_date as date,
        count(*) as total_sent,
        count(*) filter (where sending_id is not null) as total_delivered,
        0 as total_rejected,
        coalesce(sum(total_chunks), 0) as total_chunks,
        0 as total_clicks,
        count(distinct sending_id) as unique_contacts,
        0::numeric as total_cost
    from {{ ref('stg_sms_envios') }}
    where sent_date is not null
    group by tenant_id, sent_date
),

combined as (
    select
        coalesce(a.tenant_id, e.tenant_id) as tenant_id,
        coalesce(a.date, e.date) as date,
        coalesce(a.total_sent, e.total_sent) as total_sent,
        coalesce(a.total_delivered, e.total_delivered) as total_delivered,
        coalesce(a.total_rejected, e.total_rejected) as total_rejected,
        coalesce(a.total_chunks, e.total_chunks) as total_chunks,
        coalesce(a.total_clicks, e.total_clicks) as total_clicks,
        coalesce(a.unique_contacts, e.unique_contacts) as unique_contacts,
        coalesce(a.total_cost, e.total_cost) as total_cost,
        case when coalesce(a.total_sent, e.total_sent, 0) > 0
            then round(coalesce(a.total_delivered, e.total_delivered, 0)::numeric
                       / coalesce(a.total_sent, e.total_sent) * 100, 2)
            else 0
        end as delivery_rate,
        case when coalesce(a.total_sent, e.total_sent, 0) > 0
            then round(coalesce(a.total_clicks, e.total_clicks, 0)::numeric
                       / coalesce(a.total_sent, e.total_sent) * 100, 2)
            else 0
        end as ctr
    from api_stats a
    full outer join envio_stats e
        on a.tenant_id = e.tenant_id and a.date = e.date
)

select * from combined
order by date desc
