-- Staging: flatten raw_campaigns_api JSONB → one row per campaign.
-- Source: raw.raw_campaigns_api (endpoint /v1/campaign)
-- Target: public.campaigns via transform_bridge.py UPSERT
-- Note: Currently 0 campaigns exist for VISIONAMOS PROD — pipeline is ready for when they appear.

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_campaigns_api') }}
    where source_data->'data' is not null
      and jsonb_typeof(source_data->'data') = 'array'
),

flattened as (
    select
        r.tenant_id,
        coalesce(elem->>'id', elem->>'campaignId')             as campana_id,
        coalesce(elem->>'name', elem->>'title', 'Sin nombre')  as campana_nombre,
        coalesce(elem->>'channel', elem->>'type', 'push')      as canal,
        coalesce(elem->>'applicationId', '100274')              as proyecto_cuenta,
        elem->>'status'                                         as tipo_campana,
        coalesce((elem->>'sent')::int, 0)                       as total_enviados,
        coalesce((elem->>'delivered')::int, 0)                  as total_entregados,
        coalesce((elem->>'clicked')::int, 0)                    as total_clicks,
        0                                                       as total_chunks,
        (elem->>'startDate')::date                              as fecha_inicio,
        (elem->>'endDate')::date                                as fecha_fin,
        coalesce((elem->>'opened')::int, 0)                     as total_abiertos,
        coalesce((elem->>'bounced')::int, 0)                    as total_rebotes,
        coalesce((elem->>'blocked')::int, 0)                    as total_bloqueados,
        coalesce((elem->>'spam')::int, 0)                       as total_spam,
        coalesce((elem->>'unsubscribed')::int, 0)               as total_desuscritos,
        coalesce((elem->>'converted')::int, 0)                  as total_conversiones,
        r.loaded_at
    from raw_rows r,
         jsonb_array_elements(r.source_data->'data') as elem
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, campana_id
            order by loaded_at desc
        ) as _rn
    from flattened
    where campana_id is not null
)

select
    tenant_id,
    campana_id,
    campana_nombre,
    canal,
    proyecto_cuenta,
    tipo_campana,
    total_enviados,
    total_entregados,
    total_clicks,
    total_chunks,
    fecha_inicio,
    fecha_fin,
    total_abiertos,
    total_rebotes,
    total_bloqueados,
    total_spam,
    total_desuscritos,
    total_conversiones,

    -- Recalculated rates
    case when total_enviados > 0
        then round(total_clicks::numeric / total_enviados * 100, 2)
        else 0
    end as ctr,

    case when total_enviados > 0
        then round(total_entregados::numeric / total_enviados * 100, 2)
        else 0
    end as tasa_entrega,

    case when total_entregados > 0
        then round(total_abiertos::numeric / total_entregados * 100, 2)
        else 0
    end as open_rate,

    case when total_clicks > 0
        then round(total_conversiones::numeric / total_clicks * 100, 2)
        else 0
    end as conversion_rate

from deduplicated
where _rn = 1
