"""Build dim_conversation_session and update dim_conversation + fact_message_events."""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432, dbname='postgres',
    user='postgres', password='5hOnuj-FDb4V9D5Lk3LUrSuSUGgDS8k8'
)
conn.autocommit = True
cur = conn.cursor()

# ═══════════════════════════════════════════
# Step 1: int_bot_intent_bridge (as temp table)
# ═══════════════════════════════════════════
print("=== Paso 1: int_bot_intent_bridge ===")
cur.execute("DROP TABLE IF EXISTS _tmp_bot_intent_bridge CASCADE")
cur.execute("""
CREATE TEMP TABLE _tmp_bot_intent_bridge AS
WITH intent_messages AS (
    SELECT
        tenant_id, contact_id, conversation_id, intent, timestamp, date
    FROM public_staging.stg_messages
    WHERE intent IS NOT NULL
      AND intent <> ''
      AND intent NOT IN (
          'Default Welcome Intent', 'Default Fallback Intent',
          'Privacy Accepted', 'Receive Flow Response'
      )
),
agent_sessions AS (
    SELECT
        tenant_id, conversation_session_id, contact_id,
        min(queued_at) AS first_queued,
        max(closed_at) AS last_closed
    FROM public_staging.stg_chat_conversations
    WHERE conversation_session_id IS NOT NULL
    GROUP BY tenant_id, conversation_session_id, contact_id
),
matched AS (
    SELECT
        b.tenant_id, b.contact_id, b.intent,
        b.timestamp AS intent_timestamp,
        a.conversation_session_id,
        row_number() OVER (
            PARTITION BY b.tenant_id, b.contact_id, b.timestamp
            ORDER BY abs(extract(epoch FROM b.timestamp - a.first_queued))
        ) AS proximity_rank
    FROM intent_messages b
    INNER JOIN agent_sessions a
        ON a.tenant_id = b.tenant_id AND a.contact_id = b.contact_id
    WHERE b.timestamp BETWEEN a.first_queued - interval '2 hours'
                          AND coalesce(a.last_closed, a.first_queued + interval '24 hours')
)
SELECT tenant_id, conversation_session_id, contact_id, intent, intent_timestamp
FROM matched WHERE proximity_rank = 1
""")
cur.execute("SELECT count(*) FROM _tmp_bot_intent_bridge")
print(f"  Filas: {cur.fetchone()[0]}")

# Quick check
cur.execute("""
    SELECT intent, count(*) FROM _tmp_bot_intent_bridge
    GROUP BY intent ORDER BY count(*) DESC LIMIT 10
""")
print("  Top intents matched:")
for r in cur.fetchall():
    print(f"    {r[0]}: {r[1]}")

# ═══════════════════════════════════════════
# Step 2: int_conversation_sessions (as temp table)
# ═══════════════════════════════════════════
print("\n=== Paso 2: int_conversation_sessions ===")
cur.execute("DROP TABLE IF EXISTS _tmp_conversation_sessions CASCADE")
cur.execute("""
CREATE TEMP TABLE _tmp_conversation_sessions AS
WITH enriched AS (
    SELECT
        c.tenant_id, c.session_id, c.conversation_session_id,
        c.contact_id, c.agent_id, c.queued_at, c.assigned_at, c.closed_at,
        c.wait_time_seconds, c.handle_time_seconds, c.initial_session_id,
        c.total_duration_seconds
    FROM public_staging.stg_chat_conversations c
),
close_reasons_msg AS (
    SELECT tenant_id, conversation_id, close_reason,
           row_number() OVER (PARTITION BY tenant_id, conversation_id ORDER BY timestamp DESC) AS rn
    FROM public_staging.stg_messages
    WHERE close_reason IS NOT NULL AND close_reason <> ''
),
agent_agg AS (
    SELECT
        e.conversation_session_id,
        e.tenant_id,
        min(e.contact_id) AS contact_id,
        count(*) AS agent_session_count,
        min(e.queued_at) AS first_queued_at,
        max(e.closed_at) AS last_closed_at,
        sum(e.wait_time_seconds) AS total_wait_seconds,
        sum(e.handle_time_seconds) AS total_handle_seconds,
        (array_agg(cr.close_reason ORDER BY e.closed_at DESC NULLS LAST))[1] AS last_close_reason
    FROM enriched e
    LEFT JOIN close_reasons_msg cr
        ON cr.tenant_id = e.tenant_id AND cr.conversation_id = e.session_id AND cr.rn = 1
    WHERE e.conversation_session_id IS NOT NULL
    GROUP BY e.conversation_session_id, e.tenant_id
),
dominant_intent AS (
    SELECT conversation_session_id, intent AS dominant_intent,
           row_number() OVER (PARTITION BY conversation_session_id ORDER BY count(*) DESC) AS rn
    FROM _tmp_bot_intent_bridge
    GROUP BY conversation_session_id, intent
),
intent_to_reason AS (
    SELECT conversation_session_id, dominant_intent,
        CASE
            WHEN dominant_intent ILIKE '%Mesa Servicios%'
                 AND dominant_intent NOT ILIKE '%VirtualCoop%'
                 AND dominant_intent NOT ILIKE '%Coopcentral%'
                THEN 'mesa_servicios'
            WHEN dominant_intent ILIKE '%VirtualCoop%' THEN 'virtualcoop'
            WHEN dominant_intent ILIKE '%Coopcentral%' THEN 'red_coopcentral'
            WHEN dominant_intent ILIKE '%Gesti%Dispositivos%'
                 AND dominant_intent NOT ILIKE '%Devoluci%'
                 AND dominant_intent NOT ILIKE '%Solicitud%'
                 AND dominant_intent NOT ILIKE '%Traslado%'
                 AND dominant_intent NOT ILIKE '%Soporte%'
                THEN 'gestion_dispositivos'
            WHEN dominant_intent ILIKE '%Devoluci%' THEN 'devolucion'
            WHEN dominant_intent ILIKE '%Solicitud%'
              OR dominant_intent ILIKE '%Reposici%' THEN 'solicitud_reposicion'
            WHEN dominant_intent ILIKE '%Traslado%' THEN 'traslado'
            WHEN dominant_intent ILIKE '%Soporte%Novedades%' THEN 'soporte_novedades'
            WHEN dominant_intent ILIKE '%Documentaci%Red%' THEN 'documentacion_red'
            WHEN dominant_intent ILIKE '%Encuesta%' THEN 'encuesta'
            ELSE 'sin_clasificar'
        END AS reason_code
    FROM dominant_intent WHERE rn = 1
),
reason_keys AS (
    SELECT reason_code, contact_reason_key, parent_key, level
    FROM public_analytics.dim_contact_reason_seed
)
SELECT
    a.conversation_session_id,
    a.tenant_id,
    a.contact_id,
    a.first_queued_at,
    a.last_closed_at,
    CASE WHEN a.last_closed_at IS NOT NULL AND a.first_queued_at IS NOT NULL
         THEN extract(epoch FROM a.last_closed_at - a.first_queued_at)::int
    END AS total_duration_seconds,
    a.agent_session_count,
    a.total_wait_seconds,
    a.total_handle_seconds,
    a.last_close_reason,
    ir.dominant_intent,
    CASE WHEN ir.reason_code IS NOT NULL AND rk_l2.level = 2
         THEN rk_l2.parent_key
         ELSE rk_l1.contact_reason_key
    END AS contact_reason_l1_key,
    CASE WHEN rk_l2.level = 2
         THEN rk_l2.contact_reason_key
    END AS contact_reason_l2_key,
    CASE WHEN ir.dominant_intent IS NOT NULL THEN 'intent' END AS classification_method,
    ir.dominant_intent IS NOT NULL AS is_classified
FROM agent_agg a
LEFT JOIN intent_to_reason ir ON ir.conversation_session_id = a.conversation_session_id
LEFT JOIN reason_keys rk_l1 ON rk_l1.reason_code = ir.reason_code AND rk_l1.level = 1
LEFT JOIN reason_keys rk_l2 ON rk_l2.reason_code = ir.reason_code
""")
cur.execute("SELECT count(*) FROM _tmp_conversation_sessions")
print(f"  Filas: {cur.fetchone()[0]}")

# ═══════════════════════════════════════════
# Step 3: Create dim_conversation_session
# ═══════════════════════════════════════════
print("\n=== Paso 3: dim_conversation_session ===")
cur.execute("DROP TABLE IF EXISTS public_analytics.dim_conversation_session CASCADE")
cur.execute("""
CREATE TABLE public_analytics.dim_conversation_session AS
SELECT
    row_number() OVER (ORDER BY s.tenant_id, s.conversation_session_id)::int AS conversation_session_key,
    s.tenant_id,
    s.conversation_session_id,
    tn.tenant_key,
    ct.contact_key,
    s.first_queued_at,
    s.last_closed_at,
    s.total_duration_seconds,
    s.agent_session_count,
    s.total_wait_seconds,
    s.total_handle_seconds,
    s.last_close_reason,
    s.dominant_intent,
    s.contact_reason_l1_key,
    s.contact_reason_l2_key,
    s.classification_method,
    s.is_classified
FROM _tmp_conversation_sessions s
LEFT JOIN public_analytics.dim_tenant tn ON tn.tenant_id = s.tenant_id
LEFT JOIN public_analytics.dim_contact ct
    ON ct.tenant_id = s.tenant_id AND ct.contact_id = s.contact_id
""")
cur.execute("SELECT count(*) FROM public_analytics.dim_conversation_session")
print(f"  Filas: {cur.fetchone()[0]}")

# ═══════════════════════════════════════════
# Step 4: Update dim_conversation (close_reason + session FK)
# ═══════════════════════════════════════════
print("\n=== Paso 4: Actualizar dim_conversation ===")
cur.execute("DROP TABLE IF EXISTS public_analytics.dim_conversation CASCADE")
cur.execute("""
CREATE TABLE public_analytics.dim_conversation AS
WITH conversations AS (
    SELECT c.*,
        CASE WHEN c.agent_id IS NULL AND c.closed_at IS NOT NULL THEN true ELSE false END AS is_resolved_by_bot,
        CASE WHEN c.initial_session_id IS NOT NULL AND c.initial_session_id <> c.session_id THEN true ELSE false END AS is_escalated,
        coalesce(c.closed_at, c.assigned_at, c.queued_at)::date AS event_date
    FROM public_staging.stg_chat_conversations c
),
message_counts AS (
    SELECT tenant_id, conversation_id, count(*) AS message_count
    FROM public_staging.stg_messages
    WHERE conversation_id IS NOT NULL
    GROUP BY tenant_id, conversation_id
),
close_reasons AS (
    SELECT tenant_id, conversation_id, close_reason,
           row_number() OVER (PARTITION BY tenant_id, conversation_id ORDER BY timestamp DESC) AS rn
    FROM public_staging.stg_messages
    WHERE close_reason IS NOT NULL AND close_reason <> ''
),
dim_ch AS (SELECT channel_key, channel_code FROM public_analytics.dim_channel),
dim_ct AS (SELECT contact_key, tenant_id, contact_id FROM public_analytics.dim_contact WHERE contact_id IS NOT NULL),
dim_ag AS (SELECT agent_key, tenant_id, agent_id FROM public_analytics.dim_agent),
dim_css AS (SELECT conversation_session_key, tenant_id, conversation_session_id FROM public_analytics.dim_conversation_session)
SELECT
    row_number() OVER (ORDER BY c.tenant_id, c.session_id)::int AS conversation_key,
    c.tenant_id,
    c.session_id AS conversation_id,
    c.conversation_session_id,
    c.initial_session_id,
    ch.channel_key,
    ct.contact_key,
    ag.agent_key,
    css.conversation_session_key,
    c.queued_at, c.assigned_at, c.closed_at,
    cr.close_reason,
    c.wait_time_seconds, c.handle_time_seconds, c.total_duration_seconds,
    c.is_resolved_by_bot, c.is_escalated,
    coalesce(mc.message_count, 0)::int AS message_count
FROM conversations c
LEFT JOIN dim_ch ch ON ch.channel_code = CASE WHEN c.agent_id IS NOT NULL THEN 'wa_callcenter' ELSE 'wa_chatbot' END
LEFT JOIN dim_ct ct ON ct.tenant_id = c.tenant_id AND ct.contact_id = c.contact_id
LEFT JOIN dim_ag ag ON ag.tenant_id = c.tenant_id AND ag.agent_id = c.agent_id
LEFT JOIN message_counts mc ON mc.tenant_id = c.tenant_id AND mc.conversation_id = c.session_id
LEFT JOIN close_reasons cr ON cr.tenant_id = c.tenant_id AND cr.conversation_id = c.session_id AND cr.rn = 1
LEFT JOIN dim_css css ON css.tenant_id = c.tenant_id AND css.conversation_session_id = c.conversation_session_id
""")
cur.execute("SELECT count(*) FROM public_analytics.dim_conversation")
print(f"  Filas: {cur.fetchone()[0]}")

# ═══════════════════════════════════════════
# Step 5: Update fact_message_events (add conversation_session_key)
# ═══════════════════════════════════════════
print("\n=== Paso 5: Actualizar fact_message_events ===")

# Add column if not exists
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public_analytics' AND table_name = 'fact_message_events'
    AND column_name = 'conversation_session_key'
""")
if cur.fetchone() is None:
    cur.execute("ALTER TABLE public_analytics.fact_message_events ADD COLUMN conversation_session_key integer")
    print("  Columna conversation_session_key agregada")

# Update fact with session keys from dim_conversation
cur.execute("""
    UPDATE public_analytics.fact_message_events f
    SET conversation_session_key = cv.conversation_session_key
    FROM public_analytics.dim_conversation cv
    WHERE cv.conversation_key = f.conversation_key
      AND cv.conversation_session_key IS NOT NULL
""")
print(f"  Filas actualizadas en fact: {cur.rowcount}")

cur.close()
conn.close()
print("\n=== COMPLETADO ===")
