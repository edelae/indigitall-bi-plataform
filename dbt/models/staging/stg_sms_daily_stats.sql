-- Staging: sms_daily_stats — deduplicate, clean types, derive rates.

with source as (
    select * from {{ source('raw', 'sms_daily_stats') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, application_id, date
            order by total_sent desc
        ) as _rn
    from source
),

cleaned as (
    select
        tenant_id,
        application_id,
        date,
        coalesce(total_sent, 0) as total_sent,
        coalesce(total_delivered, 0) as total_delivered,
        coalesce(total_rejected, 0) as total_rejected,
        coalesce(total_chunks, 0) as total_chunks,
        coalesce(total_clicks, 0) as total_clicks,
        coalesce(unique_contacts, 0) as unique_contacts,
        coalesce(total_cost, 0) as total_cost,

        -- Derived rates
        case when coalesce(total_sent, 0) > 0
            then round(coalesce(total_delivered, 0)::numeric / total_sent * 100, 2)
            else 0
        end as delivery_rate,

        case when coalesce(total_sent, 0) > 0
            then round(coalesce(total_clicks, 0)::numeric / total_sent * 100, 2)
            else 0
        end as ctr,

        case when coalesce(total_sent, 0) > 0
            then round(coalesce(total_rejected, 0)::numeric / total_sent * 100, 2)
            else 0
        end as rejection_rate

    from deduplicated
    where _rn = 1
)

select * from cleaned
