-- Intermediate: Unified contact dimension from contacts API + conversations.
-- Contacts API has ~1,300 records; conversations reference ~21,000 unique contacts.
-- UNION both sources to ensure full coverage for FK resolution.

with api_contacts as (
    select
        tenant_id,
        contact_id,
        contact_name,
        first_contact as first_seen_date,
        last_contact as last_seen_date,
        total_messages as total_events
    from {{ ref('stg_contacts') }}
),

conversation_contacts as (
    select
        tenant_id,
        contact_id,
        null::varchar(255) as contact_name,
        min(coalesce(queued_at, assigned_at, closed_at))::date as first_seen_date,
        max(coalesce(closed_at, assigned_at, queued_at))::date as last_seen_date,
        count(*)::int as total_events
    from {{ ref('stg_chat_conversations') }}
    where contact_id is not null
    group by tenant_id, contact_id
),

unified as (
    select * from api_contacts
    union all
    select * from conversation_contacts
),

deduped as (
    select
        tenant_id,
        contact_id,
        max(contact_name) as contact_name,
        min(first_seen_date) as first_seen_date,
        max(last_seen_date) as last_seen_date,
        max(total_events) as total_events
    from unified
    group by tenant_id, contact_id
)

select * from deduped
