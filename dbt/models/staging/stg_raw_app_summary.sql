-- Staging: flatten raw_applications JSONB → one row per application.
-- Source: raw.raw_applications (endpoint /v1/application)
-- Provides app-level metadata for enrichment of other models.

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_applications') }}
    where source_data->'data' is not null
      and jsonb_typeof(source_data->'data') = 'array'
),

flattened as (
    select
        r.tenant_id,
        (elem->>'id')::varchar                          as app_id,
        elem->>'name'                                   as app_name,
        elem->>'publicKey'                              as public_key,
        (elem->>'createdAt')::timestamptz               as created_at,
        coalesce((elem->>'chatEnabled')::boolean, false)   as chat_enabled,
        coalesce((elem->>'androidEnabled')::boolean, false) as android_enabled,
        coalesce((elem->>'iosEnabled')::boolean, false)     as ios_enabled,
        coalesce((elem->>'webpushEnabled')::boolean, false) as webpush_enabled,
        -- Campaign totals from nested object
        coalesce((elem->'campaigns'->>'sent')::int, 0)      as campaigns_sent,
        coalesce((elem->'campaigns'->>'scheduled')::int, 0) as campaigns_scheduled,
        -- Device counts from nested object
        coalesce((elem->'devices'->>'android')::int, 0)     as devices_android,
        coalesce((elem->'devices'->>'ios')::int, 0)         as devices_ios,
        coalesce((elem->'devices'->>'webpush')::int, 0)     as devices_webpush,
        -- Impact totals from nested object
        coalesce((elem->'impacts'->>'total')::int, 0)       as impacts_total,
        r.loaded_at
    from raw_rows r,
         jsonb_array_elements(r.source_data->'data') as elem
    where elem->>'id' is not null
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, app_id
            order by loaded_at desc
        ) as _rn
    from flattened
)

select
    tenant_id,
    app_id,
    app_name,
    public_key,
    created_at,
    chat_enabled,
    android_enabled,
    ios_enabled,
    webpush_enabled,
    campaigns_sent,
    campaigns_scheduled,
    devices_android,
    devices_ios,
    devices_webpush,
    impacts_total
from deduplicated
where _rn = 1
