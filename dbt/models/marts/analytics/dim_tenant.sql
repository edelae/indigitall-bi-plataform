-- Dimension: tenant — single tenant configuration.

select
    1::int as tenant_key,
    'visionamos'::text as tenant_id,
    'Visionamos'::varchar(255) as tenant_name,
    '100274'::varchar(100) as app_id,
    'America/Bogota'::varchar(50) as timezone,
    true as is_active
