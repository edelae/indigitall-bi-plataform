"""Fix ALL dashboard queries with correct conversation model.

MODELO CORRECTO:
- CONVERSACION = 1 chat unico con un contacto (contact_id). Total: 664.
- SESION = 1 instancia de atencion (conversation_id). Total: 5,451.
- Solo Bot = contactos que NUNCA tuvieron conversation_id (222 contactos)
- Con Agente = contactos que tuvieron al menos 1 conversation_id (442 contactos)

CLASIFICACION DE SESIONES (por dia):
- "Solo Bot" = contact+dia con fase bot (Inbound + conversation_id IS NULL) SIN agente ese dia (357 sesiones)
- "Mixta" = contact+dia con fase bot Y agente ese dia (3,434 sesiones)
- "Solo Agente" = contact+dia con agente SIN fase bot ese dia (41 sesiones)
"""
import json
from decimal import Decimal
from datetime import date, datetime
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DB_URL)


def run_q(sql):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    data = []
    for row in rows:
        d = dict(zip(cols, row))
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
            elif isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
        data.append(d)
    return data, cols


def _store_query(qid, sql, chart_type, chart_config, name, data, cols):
    """Store query results in saved_queries (upsert)."""
    viz = [{"type": chart_type, "is_default": True, **chart_config}]
    col_meta = json.dumps([{"name": c, "type": "object"} for c in cols])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM saved_queries WHERE id = %s", (qid,))
    exists = cur.fetchone()
    if exists:
        cur.execute(
            """UPDATE saved_queries SET
                result_data = CAST(%s AS jsonb),
                result_columns = CAST(%s AS jsonb),
                generated_sql = %s,
                visualizations = CAST(%s AS jsonb),
                result_row_count = %s,
                name = %s
            WHERE id = %s""",
            [json.dumps(data), col_meta, sql, json.dumps(viz), len(data), name, qid],
        )
    else:
        cur.execute(
            """INSERT INTO saved_queries
                (id, name, query_text, generated_sql, result_data,
                 result_columns, visualizations, result_row_count)
            VALUES (%s, %s, %s, %s, CAST(%s AS jsonb),
                    CAST(%s AS jsonb), CAST(%s AS jsonb), %s)""",
            [qid, name, name, sql, json.dumps(data), col_meta,
             json.dumps(viz), len(data)],
        )
    conn.commit()
    conn.close()
    action = "UPD" if exists else "NEW"
    print(f"  [{qid}] [{action}] {name}: {len(data)} rows, cols={cols}")
    if data and len(data) <= 3:
        for d in data:
            print(f"    -> {d}")
    elif data:
        print(f"    -> {data[0]}")


def update_query(qid, sql, chart_type, chart_config, name=None):
    data, cols = run_q(sql)
    _store_query(qid, sql, chart_type, chart_config, name or f"query {qid}",
                 data, cols)


def update_query_pivoted(qid, sql, pivot_col, value_col, keep_cols,
                          chart_type, chart_config_fn, name):
    """Run SQL, pivot a column into separate columns, then store.

    Args:
        pivot_col: column whose unique values become new columns
        value_col: column whose values fill the pivoted cells
        keep_cols: columns to keep as-is (e.g. ['fecha'])
        chart_config_fn: callable(pivot_values) -> chart_config dict
    """
    data, _ = run_q(sql)
    # Preserve insertion order for pivot values
    pivot_values = []
    seen = set()
    for row in data:
        val = row[pivot_col]
        if val not in seen:
            seen.add(val)
            pivot_values.append(val)
    # Pivot
    pivoted = {}
    for row in data:
        key = tuple(row[c] for c in keep_cols)
        if key not in pivoted:
            pivoted[key] = {c: row[c] for c in keep_cols}
            for pv in pivot_values:
                pivoted[key][pv] = 0
        pivoted[key][row[pivot_col]] = row[value_col]
    final_data = sorted(pivoted.values(), key=lambda r: str(r[keep_cols[0]]))
    final_cols = keep_cols + pivot_values
    chart_config = chart_config_fn(pivot_values)
    _store_query(qid, sql, chart_type, chart_config, name, final_data, final_cols)


# =====================================================================
# Common CTE for Bot/Mixta classification at SESSION level (contact+dia)
# =====================================================================
BOT_PHASE_CTE = """
bot_phase AS (
    SELECT DISTINCT contact_id, date AS fecha
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND direction = 'Inbound'
      AND conversation_id IS NULL
),
agent_phase AS (
    SELECT DISTINCT contact_id, date AS fecha
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND conversation_id IS NOT NULL
)
"""


def main():
    print("=" * 60)
    print("FIXING ALL QUERIES — CORRECT CONVERSATION MODEL")
    print("Conversacion = contacto unico, Sesion = conversation_id")
    print("=" * 60)

    # ================================================================
    # TAB 1: WHATSAPP GENERAL — KPIs
    # ================================================================
    print("\n--- TAB 1: WhatsApp General KPIs ---")

    # 101: Total Conversaciones = contactos unicos (~664)
    update_query(101, """
SELECT COUNT(DISTINCT contact_id) AS total_conversaciones
FROM messages
WHERE tenant_id = 'visionamos'
""".strip(), "kpi", {},
        name="WA General - Total Conversaciones (Contactos Unicos)")

    # 102: Total Sesiones = contact+dia unicos (~3,832)
    # Este numero DEBE coincidir con la suma de barras del grafico 107
    update_query(102, f"""
WITH {BOT_PHASE_CTE},
all_sessions AS (
    SELECT COALESCE(bp.contact_id, ap.contact_id) AS contact_id,
           COALESCE(bp.fecha, ap.fecha) AS fecha
    FROM bot_phase bp
    FULL OUTER JOIN agent_phase ap ON bp.contact_id = ap.contact_id AND bp.fecha = ap.fecha
)
SELECT COUNT(*) AS total_sesiones
FROM all_sessions
""".strip(), "kpi", {},
        name="WA General - Total Sesiones")

    # 103: Agentes Activos — solo @visionamos.com con registros
    update_query(103, """
SELECT COUNT(DISTINCT agent_email) AS agentes_activos
FROM chat_conversations
WHERE tenant_id = 'visionamos'
  AND agent_email LIKE '%@visionamos.com'
""".strip(), "kpi", {},
        name="WA General - Agentes Activos Visionamos")

    # 104: Conversaciones Solo Bot = contactos que NUNCA escalaron (222)
    update_query(104, """
WITH con_agente AS (
    SELECT DISTINCT contact_id
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND conversation_id IS NOT NULL
)
SELECT COUNT(DISTINCT m.contact_id) AS conversaciones_solo_bot
FROM messages m
LEFT JOIN con_agente ca ON m.contact_id = ca.contact_id
WHERE m.tenant_id = 'visionamos'
  AND ca.contact_id IS NULL
""".strip(), "kpi", {},
        name="WA General - Conversaciones Solo Bot (Nunca Escalaron)")

    # 105: Conversaciones Con Agente = contactos que escalaron al menos 1 vez (442)
    update_query(105, """
SELECT COUNT(DISTINCT contact_id) AS conversaciones_con_agente
FROM messages
WHERE tenant_id = 'visionamos'
  AND conversation_id IS NOT NULL
""".strip(), "kpi", {},
        name="WA General - Conversaciones Con Agente")

    # 106: Tiempo Promedio de Atencion (min) — solo agentes Visionamos
    update_query(106, """
WITH visa_contacts AS (
    SELECT DISTINCT contact_id
    FROM messages WHERE tenant_id = 'visionamos'
)
SELECT ROUND(
    AVG(COALESCE(cc.wait_time_seconds, 0) + COALESCE(cc.handle_time_seconds, 0))::numeric / 60.0
, 1) AS tiempo_promedio_min
FROM chat_conversations cc
JOIN visa_contacts vc ON cc.contact_id = vc.contact_id
WHERE cc.tenant_id = 'visionamos'
  AND cc.agent_email LIKE '%@visionamos.com'
  AND (cc.wait_time_seconds IS NOT NULL OR cc.handle_time_seconds IS NOT NULL)
""".strip(), "kpi", {},
        name="WA General - Tiempo Promedio Atencion (min)")

    # ================================================================
    # TAB 1: WHATSAPP GENERAL — Charts
    # ================================================================
    print("\n--- TAB 1: WhatsApp General Charts ---")

    # 107: Sesiones Diarias clasificadas Solo Bot vs Mixta vs Solo Agente
    update_query(107, f"""
WITH {BOT_PHASE_CTE},
classified AS (
    SELECT COALESCE(bp.fecha, ap.fecha) AS fecha,
        CASE
            WHEN bp.contact_id IS NOT NULL AND ap.contact_id IS NULL THEN 'Solo Bot'
            WHEN bp.contact_id IS NOT NULL AND ap.contact_id IS NOT NULL THEN 'Mixta'
            WHEN bp.contact_id IS NULL AND ap.contact_id IS NOT NULL THEN 'Solo Agente'
        END AS tipo
    FROM bot_phase bp
    FULL OUTER JOIN agent_phase ap ON bp.contact_id = ap.contact_id AND bp.fecha = ap.fecha
)
SELECT fecha,
    COUNT(*) FILTER (WHERE tipo = 'Solo Bot') AS solo_bot,
    COUNT(*) FILTER (WHERE tipo = 'Mixta') AS mixta,
    COUNT(*) FILTER (WHERE tipo = 'Solo Agente') AS solo_agente
FROM classified
GROUP BY fecha
ORDER BY fecha
""".strip(), "bar_stacked", {"xKey": "fecha", "yKeys": ["solo_bot", "mixta", "solo_agente"]},
        name="WA General - Sesiones Diarias: Solo Bot vs Mixta vs Solo Agente")

    # 108: Top 10 Intenciones — tendencia diaria (pivotado para soportar granularidad)
    update_query_pivoted(108, f"""
WITH {BOT_PHASE_CTE},
intent_msgs AS (
    SELECT DISTINCT
        REGEXP_REPLACE(intent, '^\[[\d.]+\]\s*', '') AS intent_clean,
        contact_id, date AS fecha
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND intent IS NOT NULL AND intent <> ''
      AND direction = 'Inbound'
),
classified AS (
    SELECT im.intent_clean AS intent, im.fecha
    FROM intent_msgs im
),
ranked AS (
    SELECT intent, COUNT(*) AS total
    FROM classified GROUP BY intent ORDER BY total DESC LIMIT 10
)
SELECT c.fecha, c.intent, COUNT(*) AS conteo
FROM classified c
INNER JOIN ranked r ON c.intent = r.intent
GROUP BY c.fecha, c.intent
ORDER BY c.fecha, c.intent
""".strip(),
        pivot_col="intent", value_col="conteo", keep_cols=["fecha"],
        chart_type="line",
        chart_config_fn=lambda intents: {"xKey": "fecha", "yKeys": intents},
        name="WA General - Tendencia Diaria Top 10 Intenciones")

    # ================================================================
    # TAB 2: WHATSAPP BOT — KPIs
    # ================================================================
    print("\n--- TAB 2: WhatsApp Bot KPIs ---")

    # 109: Total sesiones con fase bot (contact+dia que tuvieron Inbound sin conv_id)
    update_query(109, f"""
WITH {BOT_PHASE_CTE}
SELECT COUNT(*) AS sesiones_bot_total
FROM bot_phase
""".strip(), "kpi", {},
        name="WA Bot - Sesiones con Fase Bot")

    # 110: Sesiones Solo Bot (fase bot SIN agente ese dia) = 357
    update_query(110, f"""
WITH {BOT_PHASE_CTE}
SELECT COUNT(*) AS sesiones_solo_bot
FROM bot_phase bp
LEFT JOIN agent_phase ap ON bp.contact_id = ap.contact_id AND bp.fecha = ap.fecha
WHERE ap.contact_id IS NULL
""".strip(), "kpi", {},
        name="WA Bot - Sesiones Solo Bot")

    # 111: Sesiones Mixta (fase bot + agente mismo dia) = 3,434
    update_query(111, f"""
WITH {BOT_PHASE_CTE}
SELECT COUNT(*) AS sesiones_mixta
FROM bot_phase bp
INNER JOIN agent_phase ap ON bp.contact_id = ap.contact_id AND bp.fecha = ap.fecha
""".strip(), "kpi", {},
        name="WA Bot - Sesiones Mixta (Bot + Agente)")

    # 112: Tasa Fallback — en fase bot
    update_query(112, """
SELECT ROUND(
    COUNT(*) FILTER (WHERE is_fallback = true) * 100.0 /
    NULLIF(COUNT(*), 0)
, 1) AS tasa_fallback_pct
FROM messages
WHERE tenant_id = 'visionamos'
  AND direction = 'Inbound'
  AND conversation_id IS NULL
""".strip(), "kpi", {},
        name="WA Bot - Tasa Fallback (%)")

    # 113: Intents Distintos
    update_query(113, """
SELECT COUNT(DISTINCT REGEXP_REPLACE(intent, '^\[[\d.]+\]\s*', '')) AS intents_distintos
FROM messages
WHERE tenant_id = 'visionamos'
  AND intent IS NOT NULL AND intent <> ''
""".strip(), "kpi", {},
        name="WA Bot - Intents Distintos")

    # ================================================================
    # TAB 2: WHATSAPP BOT — Charts
    # ================================================================
    print("\n--- TAB 2: WhatsApp Bot Charts ---")

    # 114: Tendencia Fallbacks Diarios — linea con solo_bot vs mixta
    update_query(114, f"""
WITH {BOT_PHASE_CTE},
fallback_contacts AS (
    SELECT DISTINCT contact_id, date AS fecha
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND is_fallback = true
      AND direction = 'Inbound'
      AND conversation_id IS NULL
)
SELECT fc.fecha,
    COUNT(*) FILTER (WHERE ap.contact_id IS NULL) AS solo_bot,
    COUNT(*) FILTER (WHERE ap.contact_id IS NOT NULL) AS mixta,
    COUNT(*) AS total_fallbacks
FROM fallback_contacts fc
LEFT JOIN agent_phase ap ON fc.contact_id = ap.contact_id AND fc.fecha = ap.fecha
GROUP BY fc.fecha
ORDER BY fc.fecha
""".strip(), "line", {"xKey": "fecha", "yKeys": ["solo_bot", "mixta", "total_fallbacks"]},
        name="WA Bot - Tendencia Fallbacks Diarios: Solo Bot vs Mixta")

    # 115: Top 10 intents en sesiones con fallback — tendencia diaria (pivotado)
    update_query_pivoted(115, f"""
WITH {BOT_PHASE_CTE},
fallback_sessions AS (
    SELECT DISTINCT contact_id, date AS fecha
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND is_fallback = true
),
session_intents AS (
    SELECT DISTINCT
        REGEXP_REPLACE(m.intent, '^\[[\d.]+\]\s*', '') AS intent,
        m.contact_id,
        m.date AS fecha
    FROM messages m
    INNER JOIN fallback_sessions fs ON m.contact_id = fs.contact_id AND m.date = fs.fecha
    WHERE m.tenant_id = 'visionamos'
      AND m.intent IS NOT NULL AND m.intent <> ''
      AND m.direction = 'Inbound'
      AND m.intent <> 'Default Fallback Intent'
),
ranked AS (
    SELECT intent, COUNT(*) AS total
    FROM session_intents GROUP BY intent ORDER BY total DESC LIMIT 10
)
SELECT si.fecha, si.intent, COUNT(*) AS conteo
FROM session_intents si
INNER JOIN ranked r ON si.intent = r.intent
GROUP BY si.fecha, si.intent
ORDER BY si.fecha, si.intent
""".strip(),
        pivot_col="intent", value_col="conteo", keep_cols=["fecha"],
        chart_type="line",
        chart_config_fn=lambda intents: {"xKey": "fecha", "yKeys": intents},
        name="WA Bot - Tendencia Diaria Top 10 Intents en Sesiones con Fallback")

    # ================================================================
    # TAB 2: WHATSAPP BOT — KPI adicional
    # ================================================================
    print("\n--- TAB 2: WhatsApp Bot KPI adicional ---")

    # 116: Total Fallbacks en sesiones bot (conteo absoluto)
    update_query(116, """
SELECT COUNT(*) AS sesiones_con_fallback
FROM (
    SELECT DISTINCT contact_id, date
    FROM messages
    WHERE tenant_id = 'visionamos'
      AND is_fallback = true
      AND direction = 'Inbound'
      AND conversation_id IS NULL
) x
""".strip(), "kpi", {},
        name="WA Bot - Sesiones con Fallback (Bot)")

    print("\n" + "=" * 60)
    print("ALL QUERIES UPDATED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
