-- Staging: flatten raw_contacts_api JSONB → one row per contact.
-- Source: raw.raw_contacts_api (endpoint /v1/chat/contacts)
-- Target: public.contacts via transform_bridge.py UPSERT

with raw_rows as (
    select
        source_data,
        coalesce(tenant_id, 'visionamos') as tenant_id,
        loaded_at
    from {{ source('raw_jsonb', 'raw_contacts_api') }}
    where source_data->'data' is not null
      and jsonb_typeof(source_data->'data') = 'array'
),

flattened as (
    select
        r.tenant_id,
        elem->>'contactId'                         as contact_id,
        elem->>'profileName'                        as contact_name,
        (elem->>'createdAt')::timestamptz::date     as first_contact,
        (elem->>'updatedAt')::timestamptz::date     as last_contact,
        elem->>'channel'                            as channel,
        (elem->>'instanceId')::int                  as instance_id,
        (elem->>'chatAllowed')::boolean             as chat_allowed,
        elem->>'agentId'                            as agent_id,
        (elem->>'lastInputMessage')::timestamptz    as last_input_message,
        r.loaded_at
    from raw_rows r,
         jsonb_array_elements(r.source_data->'data') as elem
    where elem->>'contactId' is not null
),

deduplicated as (
    select *,
        row_number() over (
            partition by tenant_id, contact_id
            order by last_contact desc nulls last, loaded_at desc
        ) as _rn
    from flattened
)

select
    tenant_id,
    contact_id,
    contact_name,
    0 as total_messages,       -- not available via ServerKey auth
    first_contact,
    last_contact,
    0 as total_conversations   -- not available via ServerKey auth
from deduplicated
where _rn = 1
