-- Mart: dim_sms_campaigns — SMS campaign dimension with enriched metrics.

{{ config(
    schema='public_marts',
    materialized='table',
) }}

with campaigns as (
    select * from {{ ref('stg_sms_campaigns') }}
),

envio_metrics as (
    select
        tenant_id,
        campaign_id,
        count(*) as actual_sendings,
        count(distinct sending_id) as unique_sendings,
        coalesce(sum(total_chunks), 0) as total_chunks,
        min(sent_date) as first_send_date,
        max(sent_date) as last_send_date,
        count(distinct sent_date) as active_days
    from {{ ref('stg_sms_envios') }}
    group by tenant_id, campaign_id
)

select
    c.tenant_id,
    c.application_id,
    c.campaign_id,
    c.name as campaign_name,
    c.status,
    c.sending_type,
    c.total_sendings as api_total_sendings,
    c.total_contacts as api_total_contacts,
    coalesce(e.actual_sendings, 0) as actual_sendings,
    coalesce(e.total_chunks, 0) as total_chunks,
    e.first_send_date,
    e.last_send_date,
    coalesce(e.active_days, 0) as active_days,
    c.created_at,
    c.updated_at
from campaigns c
left join envio_metrics e
    on c.tenant_id = e.tenant_id and c.campaign_id = e.campaign_id
