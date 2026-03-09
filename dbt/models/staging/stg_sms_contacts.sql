-- Staging: sms_contacts — deduplicate, clean types.

with source as (
    select * from {{ source('raw', 'sms_contacts') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, contact_id
            order by updated_at desc nulls last
        ) as _rn
    from source
),

cleaned as (
    select
        tenant_id,
        application_id,
        contact_id,
        phone,
        country_code,
        coalesce(total_sendings, 0) as total_sendings,
        created_at,
        updated_at
    from deduplicated
    where _rn = 1
)

select * from cleaned
