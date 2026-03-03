-- Intermediate: Unpivot toques_daily wide metrics into tall event rows.
-- 1 toques row → up to 9 fact rows (one per non-zero metric).
-- SMS rows are skipped when sms_envios has row-level data for the same date.

with toques as (
    select * from {{ ref('stg_toques_daily') }}
),

-- Detect dates that have SMS row-level data in sms_envios
sms_covered_dates as (
    select distinct
        tenant_id,
        sent_date as date
    from {{ ref('stg_sms_envios') }}
),

-- Filter out SMS toques that are covered by sms_envios
filtered_toques as (
    select t.*
    from toques t
    left join sms_covered_dates sd
        on t.tenant_id = sd.tenant_id
        and t.date = sd.date
        and lower(t.canal) = 'sms'
    where sd.date is null
),

-- Map canal to channel_code
channel_mapped as (
    select
        f.*,
        case lower(f.canal)
            when 'push' then 'push_android'
            when 'push_android' then 'push_android'
            when 'push_ios' then 'push_ios'
            when 'webpush' then 'push_web'
            when 'push_web' then 'push_web'
            when 'email' then 'email'
            when 'inapp' then 'inapp'
            when 'sms' then 'sms'
            else lower(f.canal)
        end as channel_code
    from filtered_toques f
),

-- Unpivot: one row per non-zero metric
events as (
    select tenant_id, date as event_date, channel_code, proyecto_cuenta,
           'sent' as event_code, enviados as event_count
    from channel_mapped where enviados > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'delivered', entregados
    from channel_mapped where entregados > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'clicked', clicks
    from channel_mapped where clicks > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'opened', abiertos
    from channel_mapped where abiertos > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'bounced', rebotes
    from channel_mapped where rebotes > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'blocked', bloqueados
    from channel_mapped where bloqueados > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'spam', spam
    from channel_mapped where spam > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'unsubscribed', desuscritos
    from channel_mapped where desuscritos > 0

    union all

    select tenant_id, date, channel_code, proyecto_cuenta,
           'converted', conversiones
    from channel_mapped where conversiones > 0
)

select
    tenant_id,
    event_date,
    channel_code,
    proyecto_cuenta,
    event_code,
    event_count,
    'toques_daily'::varchar(30) as source_table
from events
