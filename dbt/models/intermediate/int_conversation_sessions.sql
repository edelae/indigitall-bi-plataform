-- Intermediate: Aggregate agent sessions by conversation_session_id.
-- Enriches with bot intents and maps to contact_reason taxonomy.

with agent_agg as (
    select
        conversation_session_id,
        tenant_id,
        min(contact_id) as contact_id,
        count(*) as agent_session_count,
        min(queued_at) as first_queued_at,
        max(closed_at) as last_closed_at,
        sum(wait_time_seconds) as total_wait_seconds,
        sum(handle_time_seconds) as total_handle_seconds,
        (array_agg(close_reason order by closed_at desc nulls last))[1] as last_close_reason
    from (
        select
            e.conversation_session_id,
            e.tenant_id,
            e.contact_id,
            e.queued_at,
            e.closed_at,
            e.wait_time_seconds,
            e.handle_time_seconds,
            m.close_reason
        from {{ ref('int_conversations_enriched') }} e
        left join (
            select
                tenant_id,
                conversation_id,
                close_reason,
                row_number() over (
                    partition by tenant_id, conversation_id
                    order by timestamp desc
                ) as rn
            from {{ ref('stg_messages') }}
            where close_reason is not null
        ) m on m.tenant_id = e.tenant_id
           and m.conversation_id = e.session_id
           and m.rn = 1
    ) sub
    where conversation_session_id is not null
    group by conversation_session_id, tenant_id
),

dominant_intent as (
    select
        conversation_session_id,
        intent as dominant_intent,
        row_number() over (
            partition by conversation_session_id
            order by count(*) desc
        ) as rn
    from {{ ref('int_bot_intent_bridge') }}
    group by conversation_session_id, intent
),

intent_to_reason as (
    select
        conversation_session_id,
        dominant_intent,
        case
            when dominant_intent ilike '%Mesa Servicios%'
                 and dominant_intent not ilike '%VirtualCoop%'
                 and dominant_intent not ilike '%Coopcentral%'
                then 'mesa_servicios'
            when dominant_intent ilike '%VirtualCoop%' then 'virtualcoop'
            when dominant_intent ilike '%Coopcentral%' then 'red_coopcentral'
            when dominant_intent ilike '%Gestión%Dispositivos%'
                 and dominant_intent not ilike '%Devolución%'
                 and dominant_intent not ilike '%Solicitud%'
                 and dominant_intent not ilike '%Traslado%'
                 and dominant_intent not ilike '%Soporte%'
                then 'gestion_dispositivos'
            when dominant_intent ilike '%Devolución%' then 'devolucion'
            when dominant_intent ilike '%Solicitud%'
              or dominant_intent ilike '%Reposición%' then 'solicitud_reposicion'
            when dominant_intent ilike '%Traslado%' then 'traslado'
            when dominant_intent ilike '%Soporte%Novedades%' then 'soporte_novedades'
            when dominant_intent ilike '%Documentación%Red%' then 'documentacion_red'
            when dominant_intent ilike '%Encuesta%' then 'encuesta'
            else 'sin_clasificar'
        end as reason_code
    from dominant_intent
    where rn = 1
),

reason_keys as (
    select reason_code, contact_reason_key, parent_key, level
    from {{ ref('dim_contact_reason_seed') }}
),

final as (
    select
        a.conversation_session_id,
        a.tenant_id,
        a.contact_id,
        a.first_queued_at,
        a.last_closed_at,
        case
            when a.last_closed_at is not null and a.first_queued_at is not null
            then extract(epoch from a.last_closed_at - a.first_queued_at)::int
        end as total_duration_seconds,
        a.agent_session_count,
        a.total_wait_seconds,
        a.total_handle_seconds,
        a.last_close_reason,
        ir.dominant_intent,
        case when ir.reason_code is not null and rk_l2.level = 2
             then rk_l2.parent_key
             else rk_l1.contact_reason_key
        end as contact_reason_l1_key,
        case when rk_l2.level = 2
             then rk_l2.contact_reason_key
        end as contact_reason_l2_key,
        case when ir.dominant_intent is not null then 'intent' end as classification_method,
        ir.dominant_intent is not null as is_classified
    from agent_agg a
    left join intent_to_reason ir
        on ir.conversation_session_id = a.conversation_session_id
    left join reason_keys rk_l1
        on rk_l1.reason_code = ir.reason_code and rk_l1.level = 1
    left join reason_keys rk_l2
        on rk_l2.reason_code = ir.reason_code
)

select * from final
