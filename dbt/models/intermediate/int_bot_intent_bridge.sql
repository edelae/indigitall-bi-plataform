-- Intermediate: Bridge messages with Dialogflow intents to agent conversation sessions.
-- Intents are on inbound messages (Dialogflow NLU classification), not bot messages.
-- Matches by contact_id + temporal proximity (intent within 2h before agent queue).

with intent_messages as (
    select
        tenant_id,
        contact_id,
        conversation_id,
        intent,
        timestamp,
        date
    from {{ ref('stg_messages') }}
    where intent is not null
      and intent <> ''
      and intent not in (
          'Default Welcome Intent',
          'Default Fallback Intent',
          'Privacy Accepted',
          'Receive Flow Response'
      )
),

agent_sessions as (
    select
        tenant_id,
        conversation_session_id,
        contact_id,
        min(queued_at) as first_queued,
        max(closed_at) as last_closed
    from {{ ref('stg_chat_conversations') }}
    where conversation_session_id is not null
    group by tenant_id, conversation_session_id, contact_id
),

matched as (
    select
        b.tenant_id,
        b.contact_id,
        b.intent,
        b.timestamp as intent_timestamp,
        a.conversation_session_id,
        row_number() over (
            partition by b.tenant_id, b.contact_id, b.timestamp
            order by abs(extract(epoch from b.timestamp - a.first_queued))
        ) as proximity_rank
    from intent_messages b
    inner join agent_sessions a
        on a.tenant_id = b.tenant_id
        and a.contact_id = b.contact_id
    where b.timestamp between a.first_queued - interval '2 hours'
                          and coalesce(a.last_closed, a.first_queued + interval '24 hours')
)

select
    tenant_id,
    conversation_session_id,
    contact_id,
    intent,
    intent_timestamp
from matched
where proximity_rank = 1
