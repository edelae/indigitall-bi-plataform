-- Staging: sms_envios — deduplicate, clean types (API-only columns).

with source as (
    select * from {{ source('raw', 'sms_envios') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, sending_id
            order by sent_at desc nulls last
        ) as _rn
    from source
),

cleaned as (
    select
        tenant_id,
        application_id,
        campaign_id,
        sending_id,
        coalesce(total_chunks, 1) as total_chunks,
        sending_type,
        coalesce(is_flash, false) as is_flash,
        sent_at,
        sent_at::date as sent_date,
        extract(hour from sent_at)::smallint as sent_hour
    from deduplicated
    where _rn = 1
)

select * from cleaned
