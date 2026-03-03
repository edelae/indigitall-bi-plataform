-- Dimension: campaign — from staged campaigns and SMS campaign groups.

with api_campaigns as (
    select
        tenant_id,
        campana_id as campaign_id,
        campana_nombre as campaign_name,
        tipo_campana as campaign_type,
        canal,
        proyecto_cuenta,
        fecha_inicio as start_date,
        fecha_fin as end_date
    from {{ ref('stg_campaigns') }}
),

sms_campaigns as (
    select
        tenant_id,
        campaign_id,
        null::varchar(255) as campaign_name,
        'SMS'::varchar(50) as campaign_type,
        'sms'::varchar(30) as canal,
        null::varchar(100) as proyecto_cuenta,
        min(sent_date) as start_date,
        max(sent_date) as end_date
    from {{ ref('stg_sms_envios') }}
    where campaign_id is not null
    group by tenant_id, campaign_id
),

all_campaigns as (
    select * from api_campaigns
    union all
    select * from sms_campaigns
),

deduped as (
    select *,
        row_number() over (
            partition by tenant_id, campaign_id
            order by start_date nulls last
        ) as _rn
    from all_campaigns
),

dim_ch as (
    select channel_key, channel_code from {{ ref('dim_channel') }}
),

final as (
    select
        row_number() over (order by d.tenant_id, d.campaign_id)::int as campaign_key,
        d.tenant_id,
        d.campaign_id,
        d.campaign_name,
        d.campaign_type,
        ch.channel_key,
        d.proyecto_cuenta,
        d.start_date,
        d.end_date,
        true as is_active
    from deduped d
    left join dim_ch ch
        on ch.channel_code = case lower(d.canal)
            when 'sms' then 'sms'
            when 'push' then 'push_android'
            when 'push_android' then 'push_android'
            when 'push_ios' then 'push_ios'
            when 'webpush' then 'push_web'
            when 'email' then 'email'
            when 'inapp' then 'inapp'
            else lower(d.canal)
        end
    where d._rn = 1
)

select * from final
