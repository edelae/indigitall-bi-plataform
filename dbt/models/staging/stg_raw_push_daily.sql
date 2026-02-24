-- Staging: flatten raw_push_stats (dateStats) JSONB → one row per platform per day.
-- Source: raw.raw_push_stats (endpoint like '%/dateStats%')
-- Target: public.toques_daily via transform_bridge.py UPSERT

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        coalesce(application_id, '100274') as application_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_push_stats') }}
    where endpoint like '%/dateStats%'
      and source_data->'data' is not null
      and jsonb_typeof(source_data->'data') = 'array'
),

flattened as (
    select
        r.tenant_id,
        r.application_id                             as proyecto_cuenta,
        elem->>'platformGroup'                        as canal,
        (elem->>'statsDate')::date                    as date,
        coalesce((elem->>'numDevicesSent')::int, 0)   as enviados,
        coalesce((elem->>'numDevicesSuccess')::int, 0) as entregados,
        coalesce((elem->>'numDevicesReceived')::int, 0) as abiertos,
        coalesce((elem->>'numDevicesClicked')::int, 0) as clicks,
        r.loaded_at
    from raw_rows r,
         jsonb_array_elements(r.source_data->'data') as elem
    where elem->>'platformGroup' is not null
      and elem->>'statsDate' is not null
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, date, canal, proyecto_cuenta
            order by loaded_at desc
        ) as _rn
    from flattened
)

select
    tenant_id,
    date,
    canal,
    proyecto_cuenta,
    enviados,
    entregados,
    clicks,
    0 as chunks,
    0 as usuarios_unicos,
    abiertos,
    0 as rebotes,
    0 as bloqueados,
    0 as spam,
    0 as desuscritos,
    0 as conversiones,

    -- Recalculated rates
    case when enviados > 0
        then round(clicks::numeric / enviados * 100, 2)
        else 0
    end as ctr,

    case when enviados > 0
        then round(entregados::numeric / enviados * 100, 2)
        else 0
    end as tasa_entrega,

    case when entregados > 0
        then round(abiertos::numeric / entregados * 100, 2)
        else 0
    end as open_rate,

    0 as conversion_rate

from deduplicated
where _rn = 1
