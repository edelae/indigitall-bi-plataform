"""
AI Agent Service — SQL-only architecture.
Uses OpenAI GPT-4o (primary) and Anthropic Claude (fallback).
ALL data queries generate SQL. No pre-built functions.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List

import pandas as pd
from sqlalchemy import text

from app.services.data_service import DataService
from app.models.database import engine
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# --- SQL Guardrails ---

ALLOWED_TABLES = frozenset({
    "messages", "contacts", "agents", "daily_stats",
    "toques_daily", "campaigns", "toques_heatmap", "toques_usuario",
    "chat_conversations", "chat_channels", "chat_topics",
    "nps_surveys", "sms_envios", "sms_daily_stats",
    "dim_campaigns", "dim_contacts",
    "fct_agent_performance", "fct_daily_stats",
    "fct_messages_daily", "fct_toques_metrics",
    "public_marts.dim_campaigns", "public_marts.dim_contacts",
    "public_marts.fct_agent_performance", "public_marts.fct_daily_stats",
    "public_marts.fct_messages_daily", "public_marts.fct_toques_metrics",
})

SQL_BLOCKLIST = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|DO|CALL|SET\s+ROLE|pg_sleep|dblink)\b",
    re.IGNORECASE,
)

MAX_SQL_ROWS = 1000
SQL_TIMEOUT_MS = 10_000

# --- OpenAI Tools (SQL only) ---

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": (
                "Generate and execute a SQL SELECT query for any data analysis question. "
                "This is the ONLY way to query data. Always use this for any data-related question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query (or WITH ... SELECT CTE). Must include WHERE alias.tenant_id = '{TENANT_ID}' and LIMIT. ALWAYS use table aliases (m, cc, c, etc.) and qualify ALL columns with aliases in JOINs.",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "bar_horizontal", "bar_stacked", "line", "pie",
                                 "table", "area", "area_stacked", "scatter", "combo",
                                 "funnel", "treemap", "gauge", "kpi"],
                        "description": "Best visualization for the results.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title in Spanish.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Concise business insight in Spanish (max 3 sentences).",
                    },
                },
                "required": ["query", "chart_type", "title", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Ask the user for more information when the question is ambiguous.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The clarification question in Spanish.",
                    },
                },
                "required": ["question"],
            },
        },
    },
]


class AIAgent:
    """AI Agent — all data queries produce SQL. No pre-built functions."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.client = None
        self.openai_client = None
        self.model = "claude-sonnet-4-5-20250929"
        self.openai_model = settings.OPENAI_MODEL

        if ANTHROPIC_AVAILABLE and settings.has_ai_key:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        if OPENAI_AVAILABLE and settings.has_openai_key:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def is_available(self) -> bool:
        return self.client is not None or self.openai_client is not None

    @staticmethod
    def _friendly_error(message: str) -> Dict[str, Any]:
        return {
            "type": "conversation",
            "response": message,
            "data": None, "chart_type": None, "query_details": None,
        }

    # ------------------------------------------------------------------
    # System prompts
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        schema_desc = self.data_service.get_schema_description()
        return f"""Eres un analista de datos senior para VISIONAMOS (cooperativas financieras, Colombia). Canal principal: WhatsApp.

=== PERSONALIDAD ===
- Analitico, conciso, directo. Cero relleno.
- Cada respuesta EMPIEZA con el hallazgo principal (cifra exacta).
- Maximo 3-4 oraciones. Espanol colombiano profesional.

{schema_desc}

=== CLASIFICACION ===
1. CONVERSATION — Saludos, despedidas, agradecimientos, preguntas sobre ti
2. SQL — TODAS las preguntas sobre datos. Siempre genera SQL.
3. CLARIFICATION — Cuando la pregunta es ambigua

=== FORMATO DE RESPUESTA ===
SIEMPRE JSON valido. Sin texto fuera del JSON.

Para CONVERSATION:
{{"type": "conversation", "response": "Tu respuesta"}}

Para SQL (TODAS las consultas de datos):
{{"type": "sql", "query": "SELECT ...", "chart_type": "bar|line|pie|...", "title": "Titulo", "explanation": "Insight conciso"}}

Para CLARIFICATION:
{{"type": "clarification", "response": "Tu pregunta"}}

=== PRINCIPIO FUNDAMENTAL: CONVERSACION COMO EJE CENTRAL ===

El eje central de analisis es la **CONVERSACION**, NO el mensaje individual.
- Una conversacion agrupa multiples mensajes entre un contacto y el bot/agente.
- Para WhatsApp: conversation_id en messages agrupa mensajes de una sesion.
- Para Contact Center: chat_conversations tiene las sesiones de agente con timestamps.
- Los KPIs principales se miden POR CONVERSACION: total conversaciones, clasificacion Bot/Agente/Mixta,
  tiempo de respuesta, tasa de resolucion, escalamiento, etc.
- Solo usar conteo de mensajes cuando la pregunta es especificamente sobre volumen de mensajes.

=== MODELO DE DATOS COMPLETO (COLUMNAS REALES VERIFICADAS) ===

1. **messages** (~126K filas): Mensajes individuales de WhatsApp.
   Columnas: id, tenant_id, message_id, timestamp (TIMESTAMPTZ), date (DATE), hour (int 0-23),
   day_of_week (text en ingles), send_type, direction (Inbound|Agent|Bot|System),
   content_type, status, contact_name, contact_id, conversation_id (NULL en bot-only),
   agent_id (NULL si no hay agente), close_reason, intent (SOLO en direction=Inbound),
   is_fallback (bool), message_body (text), is_bot (bool), is_human (bool),
   wait_time_seconds (int), handle_time_seconds (int)
   - **CRITICO**: conversation_id es NULL en mensajes bot-only (~76K). Solo ~50K tienen conversation_id.
   - **CRITICO**: intent SOLO en direction='Inbound' (~26K). Estos mensajes tienen conversation_id=NULL.
   - **NO existen**: message_type, body_type (usar content_type, send_type)

2. **chat_conversations** (~45K filas): Sesiones de agente del Contact Center.
   Columnas: id, tenant_id, session_id, conversation_session_id (~22K unicos),
   contact_id, agent_id, agent_email, channel, queued_at (TIMESTAMPTZ),
   assigned_at (TIMESTAMPTZ), closed_at (TIMESTAMPTZ), initial_session_id,
   wait_time_seconds (int), handle_time_seconds (int)
   - **NO tiene columna "date"**. Usar: DATE_TRUNC('day', cc.queued_at)::date
   - **NO tiene**: accepted_at (usar assigned_at), status, source
   - Para agentes: usar cc.agent_email o cc.agent_id

3. **contacts** (~1.3K): id, tenant_id, contact_id, contact_name, total_messages, first_contact, last_contact, total_conversations

4. **agents** (~175): id, tenant_id, agent_id, total_messages, conversations_handled, avg_handle_time_seconds
   - **NO tiene**: agent_name, email, status, role. Solo tiene agent_id como identificador.
   - Para nombre de agente: usar cc.agent_email de chat_conversations

5. **nps_surveys** (~928): id, tenant_id, message_date (TIMESTAMPTZ), date (DATE), hour, day_of_week,
   month_label, contact_name, contact_id, entity, score_atencion (1-5), score_asesor (1-5),
   rapida (1-5), resuelto (1-5), volveria (1-5), nps_categoria (Promotor/Neutro/Detractor),
   comentario, agent_id, conversation_id, close_reason, canal_tipo

6. **sms_envios** (~7.2M): id, tenant_id, application_id, campaign_id, campaign_name, sending_id,
   phone, country_code, total_chunks, cost, message_text, status (sent/delivered/rejected/error),
   error_description, sending_type, is_flash, sent_at, clicks, sending_mode, cancelled
   - **sms_daily_stats** (91): id, tenant_id, date, total_sent, total_delivered, total_rejected, total_chunks, total_clicks, unique_contacts, total_cost
   - **sms_campaigns** (9): id, tenant_id, campaign_id, name, status, sending_type, total_sendings, total_contacts, created_at

7. **toques_daily** (273): id, tenant_id, date, canal, proyecto_cuenta, enviados, entregados, clicks, chunks,
   usuarios_unicos, abiertos, rebotes, bloqueados, spam, desuscritos, conversiones, ctr, tasa_entrega, open_rate, conversion_rate
   - **NO tiene**: project_name (usar proyecto_cuenta), channel_type (usar canal), sends (usar enviados), deliveries (usar entregados)
   - **toques_heatmap** (105): id, tenant_id, canal, dia_semana, hora, enviados, clicks, abiertos, conversiones, ctr, dia_orden

8. **daily_stats** (91): id, tenant_id, date, total_messages, unique_contacts, conversations, fallback_count

=== RELACIONES CRITICAS ===
- messages.conversation_id = chat_conversations.session_id (SOLO mensajes con agente)
- messages.contact_id = contacts.contact_id
- messages.agent_id = agents.agent_id (SOLO direction='Agent')
- messages.agent_id = chat_conversations.agent_id
- nps_surveys.conversation_id = chat_conversations.session_id (FK directa)
- nps_surveys.agent_id = agents.agent_id
- Mensajes con intent NO tienen conversation_id — consultar DIRECTAMENTE en messages sin JOIN

=== COMO CONSTRUIR CONVERSACIONES ===

**IMPORTANTE sobre el flujo real de Visionamos:**
1. Usuario escribe por WhatsApp → Bot responde (direction=Bot, SIN conversation_id)
2. Si el bot no puede resolver → escalamiento → se crea conversation_id y entra un agente
3. Por eso: mensajes Bot casi NUNCA tienen conversation_id (solo 15 de 4,190)
4. Las ~4,756 conversaciones con conversation_id son TODAS atendidas por agente (escaladas desde bot)
5. NO clasificar como "Bot only" vs "Agente only" — es engañoso. TODAS las conv_id son de agente.

**A) Conversaciones con agente — desde messages (con conversation_id):**
WITH conv AS (
  SELECT m.conversation_id, MIN(m.date) AS fecha, COUNT(*) AS total_msgs,
    COUNT(*) FILTER (WHERE m.direction = 'Agent') AS msgs_agente,
    COUNT(*) FILTER (WHERE m.direction = 'Inbound') AS msgs_usuario,
    COUNT(DISTINCT m.agent_id) FILTER (WHERE m.agent_id IS NOT NULL) AS num_agentes
  FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL
  GROUP BY m.conversation_id
)
- Metricas utiles: total_msgs, msgs_agente, msgs_usuario, num_agentes, fecha

**B) Interacciones Bot-only (SIN conversation_id):**
Para contar interacciones que el bot resolvio sin escalar:
SELECT m.date AS "Fecha", COUNT(DISTINCT m.contact_id) AS "Contactos Bot-only"
FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.direction = 'Bot' AND m.conversation_id IS NULL
GROUP BY 1 ORDER BY 1

**C) Contact Center — desde chat_conversations:**
SELECT DATE_TRUNC('day', cc.queued_at)::date AS "Fecha",
  COUNT(*) AS "Sesiones", COUNT(DISTINCT cc.conversation_session_id) AS "Conv Unicas"
FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1

**Para agentes**: La tabla agents NO tiene agent_name. Usar cc.agent_email de chat_conversations.

=== INTENCIONES (INTENTS) — REGLAS CRITICAS ===
- intent existe en mensajes Inbound (~26K). TODOS tienen conversation_id=NULL y is_bot=False.
- NUNCA usar COUNT(DISTINCT m.conversation_id) directo con intents — retorna 0.
- NUNCA usar BOOL_OR(is_bot) para clasificar intents — siempre es False.
- Para "intenciones por menciones": COUNT(*) directo en messages.
- SIEMPRE limpiar el prefijo numerico de los intents con: REGEXP_REPLACE(m.intent, '^\[[\d.]+\]\s*', '') AS "Intencion"
- Para "intenciones por conversacion": vincular via contact_id:
  WITH ic AS (SELECT m.contact_id, m.intent FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != ''), cc AS (SELECT DISTINCT m.contact_id, m.conversation_id FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL) SELECT REGEXP_REPLACE(ic.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(DISTINCT cc.conversation_id) AS "Conversaciones" FROM ic JOIN cc ON cc.contact_id = ic.contact_id GROUP BY 1 ORDER BY 2 DESC LIMIT 15
- Para "intenciones Bot vs Mixta": un intent es "Mixta" si el contacto tuvo agente EL MISMO DIA, "Bot" si no. SIEMPRE usar este patron exacto:
  WITH im AS (SELECT m.contact_id, m.intent, m.date FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != ''), cd AS (SELECT DISTINCT m.contact_id, m.date FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL) SELECT REGEXP_REPLACE(im.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(*) FILTER (WHERE cd.contact_id IS NULL) AS "Bot", COUNT(*) FILTER (WHERE cd.contact_id IS NOT NULL) AS "Mixta", COUNT(*) AS "Total" FROM im LEFT JOIN cd ON cd.contact_id = im.contact_id AND cd.date = im.date GROUP BY 1 ORDER BY 4 DESC LIMIT 15

=== TIPO DE GRAFICA (chart_type) ===
- "line" — datos temporales/tendencias
- "bar" — comparacion entre categorias
- "bar_stacked" — categorias con sub-grupos apilados
- "bar_horizontal" — rankings/top N
- "pie" — proporciones (max 8 categorias)
- "area" — tendencias con volumen
- "table" — datos tabulares o muchas columnas
- "kpi" — un solo numero/KPI
- "combo" — barras + linea (dual eje)

=== REGLAS SQL CRITICAS ===
- Solo SELECT (o WITH ... SELECT)
- Tablas: messages (m), contacts (c), agents (a), daily_stats (ds), chat_conversations (cc), campaigns (ca), toques_daily (td), toques_heatmap (th), nps_surveys (ns), sms_envios (se), sms_daily_stats (sd), sms_campaigns (sc)
- SIEMPRE WHERE alias.tenant_id = '{{TENANT_ID}}' y LIMIT (max 1000)
- Alias legibles en espanol (AS "Fecha", AS "Total Conversaciones")
- **CRITICO**: En JOINs SIEMPRE usar alias y calificar TODAS las columnas. NUNCA tenant_id sin alias.

=== CONSULTAS DE REFERENCIA (CONVERSACION-CENTRICAS) ===

-- Conversaciones por dia (con agente):
WITH conv AS (SELECT m.conversation_id, MIN(m.date) AS fecha, COUNT(*) AS msgs FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL GROUP BY m.conversation_id)
SELECT conv.fecha AS "Fecha", COUNT(*) AS "Conversaciones", ROUND(AVG(conv.msgs)::numeric, 1) AS "Promedio Msgs" FROM conv GROUP BY 1 ORDER BY 1 LIMIT 200

-- KPI conversaciones:
WITH conv AS (SELECT m.conversation_id, COUNT(*) AS msgs, COUNT(DISTINCT m.agent_id) FILTER (WHERE m.agent_id IS NOT NULL) AS agentes FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL GROUP BY m.conversation_id)
SELECT COUNT(*) AS "Total Conversaciones", ROUND(AVG(msgs)::numeric, 1) AS "Msgs Promedio por Conv", SUM(CASE WHEN agentes > 1 THEN 1 ELSE 0 END) AS "Multi-agente" FROM conv LIMIT 1

-- Agentes por conversaciones (usa agent_email, NO agent_name):
SELECT cc.agent_email AS "Agente", COUNT(DISTINCT cc.conversation_session_id) AS "Conversaciones" FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' AND cc.agent_email IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15

-- Contactos top por conversaciones:
WITH conv AS (SELECT m.conversation_id, m.contact_name FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL GROUP BY m.conversation_id, m.contact_name)
SELECT conv.contact_name AS "Contacto", COUNT(*) AS "Conversaciones" FROM conv GROUP BY 1 ORDER BY 2 DESC LIMIT 15

-- Conversaciones por mes:
WITH conv AS (SELECT m.conversation_id, MIN(m.date) AS fecha FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL GROUP BY m.conversation_id)
SELECT DATE_TRUNC('month', conv.fecha)::date AS "Mes", COUNT(*) AS "Conversaciones" FROM conv GROUP BY 1 ORDER BY 1 LIMIT 24

-- Intenciones top por menciones:
SELECT REGEXP_REPLACE(m.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(*) AS "Menciones" FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != '' GROUP BY 1 ORDER BY 2 DESC LIMIT 15

-- Intenciones top por conversaciones (vincula via contact_id):
WITH ic AS (SELECT m.contact_id, m.intent FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != ''), cc AS (SELECT DISTINCT m.contact_id, m.conversation_id FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL) SELECT REGEXP_REPLACE(ic.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(DISTINCT cc.conversation_id) AS "Conversaciones" FROM ic JOIN cc ON cc.contact_id = ic.contact_id GROUP BY 1 ORDER BY 2 DESC LIMIT 15

-- Intenciones particionadas Bot vs Mixta (si el contacto tuvo agente el mismo dia = Mixta):
WITH im AS (SELECT m.contact_id, m.intent, m.date FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != ''), cd AS (SELECT DISTINCT m.contact_id, m.date FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL) SELECT REGEXP_REPLACE(im.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(*) FILTER (WHERE cd.contact_id IS NULL) AS "Bot", COUNT(*) FILTER (WHERE cd.contact_id IS NOT NULL) AS "Mixta", COUNT(*) AS "Total" FROM im LEFT JOIN cd ON cd.contact_id = im.contact_id AND cd.date = im.date GROUP BY 1 ORDER BY 4 DESC LIMIT 15

-- Intenciones con fallback:
SELECT REGEXP_REPLACE(m.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(*) AS "Fallbacks" FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.is_fallback = true AND m.intent IS NOT NULL AND m.intent != '' GROUP BY 1 ORDER BY 2 DESC LIMIT 15

-- Contact Center sesiones por dia:
SELECT DATE_TRUNC('day', cc.queued_at)::date AS "Fecha", COUNT(*) AS "Sesiones", COUNT(DISTINCT cc.conversation_session_id) AS "Conversaciones" FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 100

-- Contact Center tiempos (usa assigned_at, NO accepted_at):
SELECT DATE_TRUNC('day', cc.queued_at)::date AS "Fecha", ROUND(AVG(cc.wait_time_seconds)::numeric, 0) AS "Espera Promedio (s)", ROUND(AVG(cc.handle_time_seconds)::numeric, 0) AS "Atencion Promedio (s)" FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' AND cc.assigned_at IS NOT NULL GROUP BY 1 ORDER BY 1 LIMIT 100

-- Distribucion horaria:
SELECT m.hour AS "Hora", COUNT(*) AS "Mensajes" FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 24

-- SMS tendencia:
SELECT sd.date AS "Fecha", sd.total_sent AS "Enviados", sd.total_delivered AS "Entregados", sd.total_clicks AS "Clicks" FROM sms_daily_stats sd WHERE sd.tenant_id = '{{TENANT_ID}}' ORDER BY 1 LIMIT 100

-- NPS distribucion:
SELECT ns.nps_categoria AS "Categoria", COUNT(*) AS "Encuestas", ROUND(AVG(ns.score_atencion)::numeric, 1) AS "Prom Atencion" FROM nps_surveys ns WHERE ns.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 2 DESC LIMIT 10

-- Toques por canal (usa columnas reales: canal, enviados, entregados):
SELECT td.canal AS "Canal", SUM(td.enviados) AS "Enviados", SUM(td.entregados) AS "Entregados", SUM(td.clicks) AS "Clicks" FROM toques_daily td WHERE td.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 2 DESC LIMIT 10

-- Daily stats tendencia:
SELECT ds.date AS "Fecha", ds.total_messages AS "Mensajes", ds.conversations AS "Conversaciones", ds.fallback_count AS "Fallbacks" FROM daily_stats ds WHERE ds.tenant_id = '{{TENANT_ID}}' ORDER BY 1 LIMIT 100
"""

    def _get_system_prompt_openai(self) -> str:
        schema_desc = self.data_service.get_schema_description()
        return f"""Eres un analista de datos senior para VISIONAMOS (cooperativas financieras, Colombia). Canal principal: WhatsApp.

=== PERSONALIDAD ===
- Analitico, conciso, directo. Maximo 3-4 oraciones. Espanol colombiano.

{schema_desc}

=== INSTRUCCIONES ===
- Para saludos/conversacion, responde directamente sin herramientas
- Para CUALQUIER pregunta sobre datos, SIEMPRE usa execute_sql con SQL seguro
- Si la pregunta es ambigua, usa ask_clarification
- NUNCA respondas con texto plano cuando el usuario pide datos. Siempre genera SQL.

=== PRINCIPIO FUNDAMENTAL: CONVERSACION COMO EJE CENTRAL ===
El eje central de analisis es la **CONVERSACION**, NO el mensaje individual.
- conversation_id en messages agrupa mensajes de una sesion WhatsApp.
- chat_conversations tiene sesiones de Contact Center con timestamps.
- KPIs principales: total conversaciones, clasificacion Bot/Agente/Mixta, escalamiento, fallback por conv.
- Solo usar conteo de mensajes cuando la pregunta es especificamente sobre volumen de mensajes.
- Para clasificar: CTE con BOOL_OR(is_bot)/BOOL_OR(is_human) GROUP BY conversation_id.

=== MODELO DE DATOS (COLUMNAS REALES VERIFICADAS) ===
1. **messages** (~126K): id, tenant_id, message_id, timestamp, date (DATE), hour, day_of_week, send_type, direction (Inbound|Agent|Bot|System), content_type, status, contact_name, contact_id, conversation_id (NULL en bot-only ~76K), agent_id, close_reason, intent (SOLO en Inbound ~26K, conv_id=NULL), is_fallback, message_body, is_bot, is_human, wait_time_seconds, handle_time_seconds. NO existen: message_type, body_type.
2. **chat_conversations** (~45K): session_id, conversation_session_id (~22K unicos), contact_id, agent_id, agent_email, channel, queued_at (TIMESTAMPTZ), assigned_at (TIMESTAMPTZ), closed_at, initial_session_id, wait_time_seconds, handle_time_seconds. NO tiene: "date" (usar queued_at), accepted_at (usar assigned_at), status, source.
3. **contacts** (~1.3K): contact_id, contact_name, total_messages, first_contact, last_contact, total_conversations
4. **agents** (~175): agent_id, total_messages, conversations_handled, avg_handle_time_seconds. NO tiene: agent_name, email, status, role. Para nombre: usar cc.agent_email.
5. **nps_surveys** (~928): date, score_atencion, score_asesor, rapida, resuelto, volveria, nps_categoria, contact_name, contact_id, entity, agent_id, conversation_id, canal_tipo, comentario
6. **sms_envios** (~7.2M): sending_id, campaign_id, campaign_name, phone, sent_at, status, clicks, cost, total_chunks. sms_daily_stats (91): date, total_sent, total_delivered, total_clicks, total_cost. sms_campaigns (9): campaign_id, name, total_sendings
7. **toques_daily** (273): date, canal (NO channel_type), proyecto_cuenta (NO project_name), enviados (NO sends), entregados (NO deliveries), clicks, chunks
8. **daily_stats** (91): date, total_messages, unique_contacts, conversations, fallback_count

=== RELACIONES ===
- messages.conversation_id = chat_conversations.session_id (SOLO con agente)
- nps_surveys.conversation_id = chat_conversations.session_id
- INTENTS: conversation_id=NULL y is_bot=False en TODOS los msgs con intent. NUNCA COUNT(DISTINCT conversation_id) ni BOOL_OR(is_bot) con intents. Para Bot vs Mixta usar: WITH im AS (SELECT contact_id, intent, date FROM messages WHERE intent IS NOT NULL AND intent <> ''), cd AS (SELECT DISTINCT contact_id, date FROM messages WHERE conversation_id IS NOT NULL) SELECT im.intent, COUNT(*) FILTER (WHERE cd.contact_id IS NULL) AS Bot, COUNT(*) FILTER (WHERE cd.contact_id IS NOT NULL) AS Mixta FROM im LEFT JOIN cd ON cd.contact_id = im.contact_id AND cd.date = im.date GROUP BY 1
- messages.date (DATE) vs chat_conversations.queued_at (TIMESTAMP)

=== FLUJO DE CONVERSACIONES ===
TODAS las conversaciones con conversation_id son atendidas por agente (escaladas desde bot).
Mensajes Bot casi NUNCA tienen conversation_id (solo 15 de 4,190).
NO clasificar Bot/Agente/Mixta con is_bot/is_human — es engañoso. Usar metricas de agente.

=== REGLAS SQL ===
- Solo SELECT/WITH. SIEMPRE WHERE alias.tenant_id = '{{TENANT_ID}}' y LIMIT (max 1000)
- En JOINs: SIEMPRE alias y calificar TODAS las columnas. NUNCA tenant_id sin alias.
- Alias legibles en espanol. SIEMPRE incluir chart_type adecuado.

=== CONSULTAS DE REFERENCIA ===
Conv por dia: WITH conv AS (SELECT m.conversation_id, MIN(m.date) AS fecha, COUNT(*) AS msgs FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL GROUP BY m.conversation_id) SELECT conv.fecha AS "Fecha", COUNT(*) AS "Conversaciones", ROUND(AVG(conv.msgs)::numeric,1) AS "Msgs Promedio" FROM conv GROUP BY 1 ORDER BY 1 LIMIT 200
Agentes (usa agent_email, NO agent_name): SELECT cc.agent_email AS "Agente", COUNT(DISTINCT cc.conversation_session_id) AS "Conversaciones" FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' AND cc.agent_email IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15
Intenciones por menciones: SELECT REGEXP_REPLACE(m.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(*) AS "Menciones" FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != '' GROUP BY 1 ORDER BY 2 DESC LIMIT 15
Intenciones por conv (via contact_id): WITH ic AS (SELECT m.contact_id, m.intent FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.intent IS NOT NULL AND m.intent != ''), cc AS (SELECT DISTINCT m.contact_id, m.conversation_id FROM messages m WHERE m.tenant_id = '{{TENANT_ID}}' AND m.conversation_id IS NOT NULL) SELECT REGEXP_REPLACE(ic.intent, '^\[[\d.]+\]\s*', '') AS "Intencion", COUNT(DISTINCT cc.conversation_id) AS "Conversaciones" FROM ic JOIN cc ON cc.contact_id = ic.contact_id GROUP BY 1 ORDER BY 2 DESC LIMIT 15
CC tiempos (usa wait_time_seconds, assigned_at): SELECT DATE_TRUNC('day', cc.queued_at)::date AS "Fecha", ROUND(AVG(cc.wait_time_seconds)::numeric, 0) AS "Espera (s)", ROUND(AVG(cc.handle_time_seconds)::numeric, 0) AS "Atencion (s)" FROM chat_conversations cc WHERE cc.tenant_id = '{{TENANT_ID}}' AND cc.assigned_at IS NOT NULL GROUP BY 1 ORDER BY 1 LIMIT 100
Toques (columnas reales): SELECT td.canal AS "Canal", SUM(td.enviados) AS "Enviados", SUM(td.entregados) AS "Entregados" FROM toques_daily td WHERE td.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 2 DESC LIMIT 10
SMS: SELECT sd.date AS "Fecha", sd.total_sent AS "Enviados", sd.total_delivered AS "Entregados" FROM sms_daily_stats sd WHERE sd.tenant_id = '{{TENANT_ID}}' ORDER BY 1 LIMIT 100
NPS: SELECT ns.nps_categoria AS "Categoria", COUNT(*) AS "Encuestas", ROUND(AVG(ns.score_atencion)::numeric, 1) AS "Prom Atencion" FROM nps_surveys ns WHERE ns.tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 2 DESC LIMIT 10
"""

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_query(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return self._process_query_inner(user_question, conversation_history, tenant_filter)
        except Exception as e:
            logger.error("Unexpected error in process_query: %s", e)
            return self._friendly_error(
                "Ocurrio un error inesperado. Por favor intenta reformular tu pregunta."
            )

    def _process_query_inner(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        # OpenAI GPT-4o (primary)
        if self.openai_client is not None:
            result = self._openai_query(user_question, conversation_history, tenant_filter)
            if result is not None:
                return result

        # Anthropic Claude (secondary)
        if self.client is not None:
            result = self._ai_query(user_question, conversation_history, tenant_filter)
            if result is not None:
                return result

        # No AI provider available
        logger.warning("No AI provider available")
        return self._friendly_error(
            "No hay servicio de IA configurado. Contacta al administrador."
        )

    # ------------------------------------------------------------------
    # Claude (Anthropic)
    # ------------------------------------------------------------------

    def _ai_query(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            messages = []
            if conversation_history:
                for msg in conversation_history[-8:]:
                    if msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_question})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                system=self._get_system_prompt(),
                messages=messages,
            )

            response_text = response.content[0].text
            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group())
                else:
                    return None

            resp_type = response_json.get("type", "conversation")

            if resp_type in ("conversation", "clarification"):
                return {
                    "type": "conversation",
                    "response": response_json.get("response", ""),
                    "data": None, "chart_type": None, "query_details": None,
                }

            if resp_type == "sql":
                return self._execute_guarded_sql(
                    response_json.get("query", ""),
                    response_json.get("explanation", ""),
                    tenant_filter,
                    chart_type=response_json.get("chart_type"),
                    title=response_json.get("title"),
                )

            return None

        except anthropic.AuthenticationError:
            return self._friendly_error("Problema de configuracion del servicio de IA.")
        except anthropic.RateLimitError:
            return self._friendly_error("Servicio de IA ocupado. Intenta en unos segundos.")
        except anthropic.APIConnectionError:
            return self._friendly_error("No se pudo conectar con el servicio de IA.")
        except Exception as e:
            logger.warning("AI query failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # OpenAI GPT-4o
    # ------------------------------------------------------------------

    def _openai_query(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            messages = [{"role": "system", "content": self._get_system_prompt_openai()}]
            if conversation_history:
                for msg in conversation_history[-8:]:
                    if msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_question})

            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
            )

            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                return self._handle_tool_calls(message.tool_calls, tenant_filter)

            if message.content:
                return {
                    "type": "conversation",
                    "response": message.content,
                    "data": None, "chart_type": None, "query_details": None,
                }
            return None

        except openai.AuthenticationError:
            return self._friendly_error("Problema de configuracion del servicio de IA.")
        except openai.RateLimitError:
            return self._friendly_error("Servicio de IA ocupado. Intenta en unos segundos.")
        except openai.APIConnectionError:
            return self._friendly_error("No se pudo conectar con el servicio de IA.")
        except Exception as e:
            logger.error("OpenAI query failed: %s", e)
            return None

    def _handle_tool_calls(self, tool_calls, tenant_filter: Optional[str]) -> Optional[Dict[str, Any]]:
        tool_call = tool_calls[0]
        func_name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return None

        if func_name == "execute_sql":
            return self._execute_guarded_sql(
                args.get("query", ""),
                args.get("explanation", ""),
                tenant_filter,
                chart_type=args.get("chart_type"),
                title=args.get("title"),
            )

        if func_name == "ask_clarification":
            return {
                "type": "conversation",
                "response": args.get("question", ""),
                "data": None, "chart_type": None, "query_details": None,
            }

        return None

    # ------------------------------------------------------------------
    # Guarded SQL execution
    # ------------------------------------------------------------------

    def _execute_guarded_sql(
        self,
        raw_sql: str,
        explanation: str,
        tenant_filter: Optional[str] = None,
        chart_type: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        sql = raw_sql.strip().rstrip(";")

        # 1. Must be SELECT or WITH
        sql_upper = sql.upper().lstrip()
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return self._sql_error("Solo se permiten consultas SELECT.")

        # 2. Keyword blocklist
        if SQL_BLOCKLIST.search(sql):
            return self._sql_error("La consulta contiene operaciones no permitidas.")

        # 3. Only allowed tables (exclude CTE aliases)
        cte_pattern = re.compile(r"\b(\w+)\s+AS\s*\(", re.IGNORECASE)
        cte_names = {m.lower() for m in cte_pattern.findall(sql)}
        table_pattern = re.compile(r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE)
        referenced_tables = {m.lower() for m in table_pattern.findall(sql)}
        referenced_tables -= cte_names
        disallowed = referenced_tables - ALLOWED_TABLES
        if disallowed:
            return self._sql_error(
                f"Tablas no permitidas: {', '.join(disallowed)}. "
                f"Tablas disponibles: {', '.join(sorted(ALLOWED_TABLES))}"
            )

        # 4. Inject tenant_id
        tenant = tenant_filter or settings.DEFAULT_TENANT
        sql = sql.replace("{TENANT_ID}", tenant)
        if "tenant_id" not in sql.lower():
            # Find the first FROM table (with optional alias) to qualify tenant_id
            first_table_match = re.search(r"(?i)FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+(?:AS\s+)?([a-zA-Z_]\w*)?", sql)
            alias = first_table_match.group(2) if first_table_match and first_table_match.group(2) else None
            tid_col = f"{alias}.tenant_id" if alias else "tenant_id"
            if " WHERE " in sql.upper():
                sql = re.sub(r"(?i)\bWHERE\b", f"WHERE {tid_col} = '{tenant}' AND", sql, count=1)
            else:
                insert_after = first_table_match.end() if first_table_match else None
                if insert_after and alias:
                    sql = sql[:insert_after] + f" WHERE {tid_col} = '{tenant}'" + sql[insert_after:]
                else:
                    sql = re.sub(r"(?i)(FROM\s+[a-zA-Z_][a-zA-Z0-9_.]*)", rf"\1 WHERE tenant_id = '{tenant}'", sql, count=1)

        # 4b. Fix ambiguous tenant_id in JOINs — qualify bare tenant_id with first FROM alias
        has_join = bool(re.search(r"\bJOIN\b", sql, re.IGNORECASE))
        if has_join:
            first_table_match = re.search(r"(?i)FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+(?:AS\s+)?([a-zA-Z_]\w*)", sql)
            if first_table_match and first_table_match.group(2):
                alias = first_table_match.group(2)
                # Replace bare tenant_id references (not already qualified with alias.)
                sql = re.sub(r"(?<![a-zA-Z0-9_.])\btenant_id\b", f"{alias}.tenant_id", sql)

        # 5. Enforce LIMIT
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {MAX_SQL_ROWS}"

        # 6. Execute
        try:
            with engine.connect() as conn:
                conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))
                df = pd.read_sql(text(sql), conn)

            resolved_chart = chart_type or self._auto_detect_chart_type(df)
            return {
                "type": "sql",
                "response": explanation,
                "data": df,
                "chart_type": resolved_chart,
                "query_details": {
                    "function": "sql_query",
                    "sql": sql,
                    "rows_returned": len(df),
                    "title": title,
                },
            }
        except Exception as e:
            logger.warning("SQL execution failed: %s — Query: %s", e, sql)
            return self._sql_error(f"Error ejecutando la consulta: {str(e)[:200]}")

    @staticmethod
    def _auto_detect_chart_type(df: pd.DataFrame) -> str:
        if df.empty or len(df.columns) < 2:
            return "table"
        x_col = df.columns[0]
        x_lower = x_col.lower()
        n_rows = len(df)
        if any(kw in x_lower for kw in ["date", "fecha", "time", "dia", "mes", "month", "week", "periodo", "semana"]):
            return "line"
        if n_rows <= 6 and len(df.columns) == 2:
            return "pie"
        if len(df.columns) > 4 or n_rows > 50:
            return "table"
        return "bar"

    @staticmethod
    def _sql_error(message: str) -> Dict[str, Any]:
        return {
            "type": "error",
            "response": f"No pude ejecutar esa consulta. {message}",
            "data": None, "chart_type": None, "query_details": None,
        }

    # ------------------------------------------------------------------
    # Suggested questions
    # ------------------------------------------------------------------

    @staticmethod
    def get_suggested_questions() -> List[str]:
        return [
            "Dame un resumen general de los datos",
            "Cual es la tasa de fallback del bot?",
            "Mensajes por hora del dia",
            "Top 10 contactos mas activos",
            "Rendimiento de agentes",
            "Tendencia de mensajes en el tiempo",
            "Conversaciones por mes clasificadas por Bot, Agente y Mixta",
            "Top intenciones que producen fallback",
            "KPIs del Contact Center",
        ]
