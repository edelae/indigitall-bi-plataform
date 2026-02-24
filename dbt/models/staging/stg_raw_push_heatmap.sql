-- Staging: flatten raw_push_stats (pushHeatmap) JSONB → one row per weekday × hour.
-- Source: raw.raw_push_stats (endpoint like '%/pushHeatmap%')
-- Target: public.toques_heatmap via transform_bridge.py UPSERT
--
-- The heatmap JSON structure is:
--   source_data.data.weekday-hour.{weekday}.{hour} = engagement_rate (float)

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_push_stats') }}
    where endpoint like '%/pushHeatmap%'
      and source_data->'data' is not null
      and jsonb_typeof(source_data->'data') = 'object'
),

-- Pick the most recent heatmap snapshot per tenant
latest as (
    select *,
        row_number() over (partition by tenant_id order by loaded_at desc) as _rn
    from raw_rows
),

weekday_entries as (
    select
        l.tenant_id,
        weekday_key,
        weekday_val
    from latest l,
         jsonb_each(l.source_data->'data'->'weekday-hour') as wd(weekday_key, weekday_val)
    where l._rn = 1
      and jsonb_typeof(weekday_val) = 'object'
),

flattened as (
    select
        w.tenant_id,
        'push' as canal,
        w.weekday_key as dia_semana,
        hour_key::smallint as hora,
        round((hour_val::text)::numeric * 100, 2) as ctr,
        -- Map weekday name to sort order
        case w.weekday_key
            when 'monday'    then 1
            when 'tuesday'   then 2
            when 'wednesday' then 3
            when 'thursday'  then 4
            when 'friday'    then 5
            when 'saturday'  then 6
            when 'sunday'    then 7
            else 0
        end as dia_orden
    from weekday_entries w,
         jsonb_each(w.weekday_val) as h(hour_key, hour_val)
)

select
    tenant_id,
    canal,
    dia_semana,
    hora,
    0 as enviados,      -- heatmap only has engagement rates, not counts
    0 as clicks,
    0 as abiertos,
    0 as conversiones,
    ctr,
    dia_orden
from flattened
