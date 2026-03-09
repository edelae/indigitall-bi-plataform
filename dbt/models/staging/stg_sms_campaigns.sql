-- Staging: sms_campaigns — deduplicate, clean types.

with source as (
    select * from {{ source('raw', 'sms_campaigns') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, campaign_id
            order by updated_at desc nulls last
        ) as _rn
    from source
),

cleaned as (
    select
        tenant_id,
        application_id,
        campaign_id,
        name,
        status,
        sending_type,
        coalesce(total_sendings, 0) as total_sendings,
        coalesce(total_contacts, 0) as total_contacts,
        created_at,
        updated_at
    from deduplicated
    where _rn = 1
)

select * from cleaned
