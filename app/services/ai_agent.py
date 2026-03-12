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
                        "description": "The SQL SELECT query (or WITH ... SELECT CTE). Must include WHERE tenant_id = '{TENANT_ID}' and LIMIT.",
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

=== MODELO DE DATOS CRITICO ===
1. **chat_conversations** (~45K filas): Cada fila = SESION DE AGENTE.
   - conversation_session_id = conversacion logica (~22K). Usar COUNT(DISTINCT conversation_session_id)
   - NO tiene columna "date". Usar queued_at (TIMESTAMP): DATE_TRUNC('month', queued_at)
   - Ejemplo: SELECT DATE_TRUNC('month', queued_at)::date AS periodo, COUNT(DISTINCT conversation_session_id) AS conversaciones FROM chat_conversations WHERE tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 100

2. **messages** (~126K filas): Cada mensaje individual.
   - conversation_id = session_id de chat_conversations
   - Tiene columna "date" (DATE) para agrupar por fecha
   - Para Bot/Humano, clasificar a nivel conversacion:
     WITH conv_flags AS (SELECT conversation_id, BOOL_OR(is_bot) AS has_bot, BOOL_OR(is_human) AS has_human, BOOL_OR(is_fallback) AS had_fallback FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND conversation_id IS NOT NULL GROUP BY conversation_id)
   - Categorias: Bot (has_bot AND NOT has_human), Agente (has_human AND NOT has_bot), Mixta (has_bot AND has_human)

3. **nps_surveys** (928): score_atencion, score_asesor, nps_categoria, canal_tipo, entity

4. CRITICO: messages tiene "date" (DATE), chat_conversations tiene "queued_at" (TIMESTAMP). NUNCA usar "date" en chat_conversations.

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

=== REGLAS SQL ===
- Solo SELECT (o WITH ... SELECT)
- Tablas core: messages, contacts, agents, daily_stats, chat_conversations, campaigns, toques_daily, toques_heatmap, nps_surveys, sms_envios, sms_daily_stats
- Tablas marts: public_marts.dim_campaigns, public_marts.dim_contacts, public_marts.fct_agent_performance, public_marts.fct_daily_stats, public_marts.fct_messages_daily, public_marts.fct_toques_metrics
- SIEMPRE incluir WHERE tenant_id = '{{TENANT_ID}}'
- SIEMPRE incluir LIMIT (max 1000)
- Alias legibles en espanol (AS "Fecha", AS "Total Mensajes")

=== CONSULTAS COMUNES (SQL de referencia) ===

Resumen general:
SELECT 'Mensajes' AS "Metrica", COUNT(*)::text AS "Valor" FROM messages WHERE tenant_id = '{{TENANT_ID}}'
UNION ALL SELECT 'Contactos', COUNT(DISTINCT contact_id)::text FROM messages WHERE tenant_id = '{{TENANT_ID}}'
UNION ALL SELECT 'Conversaciones', COUNT(DISTINCT conversation_id)::text FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND conversation_id IS NOT NULL
LIMIT 10

Tasa de fallback:
SELECT COUNT(*) FILTER (WHERE is_fallback) AS "Fallbacks", COUNT(*) AS "Total", ROUND(100.0 * COUNT(*) FILTER (WHERE is_fallback) / NULLIF(COUNT(*), 0), 1) AS "Tasa %" FROM messages WHERE tenant_id = '{{TENANT_ID}}' LIMIT 1

Mensajes por hora:
SELECT hour AS "Hora", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 24

Tendencia diaria:
SELECT date AS "Fecha", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 100

Top contactos:
SELECT contact_name AS "Contacto", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND contact_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10

Distribucion de intenciones:
SELECT intent AS "Intencion", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND intent IS NOT NULL AND intent != '' GROUP BY 1 ORDER BY 2 DESC LIMIT 10

Rendimiento de agentes:
SELECT agent_id AS "Agente", COUNT(*) AS "Mensajes", COUNT(DISTINCT conversation_id) AS "Conversaciones" FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND agent_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15

Mensajes por dia de semana:
SELECT day_of_week AS "Dia", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY CASE day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END LIMIT 7
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

=== MODELO DE DATOS CRITICO ===
1. chat_conversations: Cada fila = SESION DE AGENTE (~45K). COUNT(DISTINCT conversation_session_id) para conversaciones reales (~22K). NO tiene "date" — usar queued_at (TIMESTAMP)
2. messages (~126K): conversation_id = session_id. Tiene "date" (DATE). Bot/Humano: BOOL_OR por conversation_id
3. nps_surveys (928): score_atencion, score_asesor, nps_categoria, canal_tipo, entity
4. CRITICO: messages.date (DATE) vs chat_conversations.queued_at (TIMESTAMP). NUNCA "date" en chat_conversations.

=== REGLAS SQL ===
- Solo SELECT (o WITH ... SELECT)
- Tablas core: messages, contacts, agents, daily_stats, chat_conversations, campaigns, toques_daily, toques_heatmap, nps_surveys, sms_envios, sms_daily_stats
- Tablas marts: public_marts.dim_campaigns, public_marts.dim_contacts, etc.
- SIEMPRE WHERE tenant_id = '{{TENANT_ID}}' y LIMIT
- Alias legibles en espanol

=== CONSULTAS DE REFERENCIA ===
Resumen: SELECT 'Mensajes' AS "Metrica", COUNT(*)::text AS "Valor" FROM messages WHERE tenant_id = '{{TENANT_ID}}' UNION ALL SELECT 'Contactos', COUNT(DISTINCT contact_id)::text FROM messages WHERE tenant_id = '{{TENANT_ID}}' LIMIT 10
Fallback: SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE is_fallback) / NULLIF(COUNT(*), 0), 1) AS "Tasa Fallback %" FROM messages WHERE tenant_id = '{{TENANT_ID}}' LIMIT 1
Tendencia: SELECT date AS "Fecha", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' GROUP BY 1 ORDER BY 1 LIMIT 100
Top contactos: SELECT contact_name AS "Contacto", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND contact_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10
Agentes: SELECT agent_id AS "Agente", COUNT(*) AS "Mensajes" FROM messages WHERE tenant_id = '{{TENANT_ID}}' AND agent_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15
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
            if " WHERE " in sql.upper():
                sql = re.sub(r"(?i)\bWHERE\b", f"WHERE tenant_id = '{tenant}' AND", sql, count=1)
            else:
                sql = re.sub(r"(?i)(FROM\s+[a-zA-Z_][a-zA-Z0-9_.]*)", rf"\1 WHERE tenant_id = '{tenant}'", sql, count=1)

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
