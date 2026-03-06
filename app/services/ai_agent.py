"""
AI Agent Service — Hybrid architecture: pre-built functions + guarded SQL fallback.
Uses OpenAI GPT-4o with function calling (primary) and Anthropic Claude (fallback).
Falls back to keyword matching (demo mode) when no API key is configured.
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

# Try to import anthropic, allow demo mode without it
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Try to import openai, allow fallback without it
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# --- SQL Guardrails ---

ALLOWED_TABLES = frozenset({
    # Core tables (public schema)
    "messages", "contacts", "agents", "daily_stats",
    "toques_daily", "campaigns", "toques_heatmap", "toques_usuario",
    "chat_conversations", "chat_channels", "chat_topics",
    # Analytics star schema (public_analytics schema)
    "fact_message_events", "dim_date", "dim_time", "dim_channel",
    "dim_event_type", "dim_tenant", "dim_contact", "dim_agent",
    "dim_campaign", "dim_conversation",
    # Schema-qualified names
    "public_analytics.fact_message_events", "public_analytics.dim_date",
    "public_analytics.dim_time", "public_analytics.dim_channel",
    "public_analytics.dim_event_type", "public_analytics.dim_tenant",
    "public_analytics.dim_contact", "public_analytics.dim_agent",
    "public_analytics.dim_campaign", "public_analytics.dim_conversation",
})

SQL_BLOCKLIST = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|DO|CALL|SET\s+ROLE|pg_sleep|dblink)\b",
    re.IGNORECASE,
)

MAX_SQL_ROWS = 1000
SQL_TIMEOUT_MS = 10_000  # 10 seconds

# --- OpenAI Function Calling Tools ---

ANALYTICS_FUNCTIONS = [
    "summary", "fallback_rate", "messages_by_direction", "messages_by_hour",
    "messages_over_time", "messages_by_day_of_week", "top_contacts",
    "intent_distribution", "agent_performance", "entity_comparison",
    "high_messages_day", "high_messages_week", "high_messages_month",
]

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_analytics",
            "description": (
                "Execute a pre-built analytics function. Use this for common queries "
                "like summaries, fallback rates, message trends, top contacts, agent performance, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "enum": ANALYTICS_FUNCTIONS,
                        "description": "The analytics function to execute.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Business insight explanation in Spanish for the user.",
                    },
                },
                "required": ["function_name", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": (
                "Generate and execute a custom SQL query for complex data analysis not covered "
                "by pre-built functions. Only SELECT queries are allowed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query. Must include WHERE tenant_id = '{TENANT_ID}' and LIMIT.",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "bar_horizontal", "bar_stacked", "line", "pie", "table", "histogram", "area", "area_stacked", "scatter", "combo", "funnel", "treemap", "gauge", "kpi"],
                        "description": "Best visualization type for the results. Use 'kpi' when the user asks for a KPI card with a single numeric value.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title in Spanish.",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Business insight explanation in Spanish for the user.",
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
    """AI Agent for natural language query processing with pre-built analytics."""

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
        """Check if any AI provider is available."""
        return self.client is not None or self.openai_client is not None

    @staticmethod
    def _friendly_error(message: str) -> Dict[str, Any]:
        """Return a user-friendly error as a conversation response."""
        return {
            "type": "conversation",
            "response": message,
            "data": None,
            "chart_type": None,
            "query_details": None,
        }

    # ------------------------------------------------------------------
    # System prompts
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        schema_desc = self.data_service.get_schema_description()
        return f"""Eres un analista de datos senior especializado en WhatsApp Business y campanas de comunicacion omnicanal para VISIONAMOS (red de cooperativas financieras en Colombia).

=== TU PERSONALIDAD ===
- Analitico, conciso y directo. Cero relleno.
- Cada respuesta EMPIEZA con el hallazgo principal (dato concreto, cifra exacta).
- Nunca expliques por que un dato es util o importante. El usuario ya lo sabe.
- Si hay algo llamativo en los datos (anomalia, pico, concentracion), mencionalo brevemente.
- Formato: hallazgo principal → dato destacado → observacion breve si aplica. Maximo 3-4 oraciones.
- Ejemplo bueno: "La hora pico es las 16:00 con 15,960 mensajes, seguida de las 15:00 con 15,655. La actividad se concentra entre 12:00 y 21:00 representando el 94% del total."
- Ejemplo malo: "Analizar los horarios de mayor actividad es muy util para tu operacion porque te permite..."
- Respondes en espanol colombiano, profesional y directo.

{schema_desc}

=== CLASIFICACION ===
Clasifica cada mensaje en UNA de estas categorias:

1. CONVERSATION — Saludos, despedidas, agradecimientos, preguntas sobre ti
2. ANALYTICS — Preguntas sobre datos que requieren una funcion de analisis
3. SQL — Preguntas complejas que NO cubren las funciones pre-built
4. CLARIFICATION — Cuando la pregunta es ambigua o necesitas mas informacion

=== FORMATO DE RESPUESTA ===
SIEMPRE responde con JSON valido. Sin texto fuera del JSON.

Para CONVERSATION:
{{"type": "conversation", "response": "Tu respuesta amigable"}}

Para ANALYTICS (funciones pre-built):
{{"type": "analytics", "function": "NOMBRE_DE_FUNCION", "explanation": "Explicacion con insight de negocio"}}

Para SQL (consultas ad-hoc):
{{"type": "sql", "query": "SELECT ... FROM ... WHERE tenant_id = '{{TENANT_ID}}' ...", "chart_type": "bar|line|pie|table|histogram|area", "title": "Titulo de la grafica", "explanation": "Que muestra esta consulta"}}

Para CLARIFICATION (cuando necesitas mas info):
{{"type": "clarification", "response": "Tu pregunta especifica para el usuario"}}

=== SELECCION DE TIPO DE GRAFICA (chart_type) ===
Cuando devuelvas tipo "sql", SIEMPRE incluye chart_type con el tipo mas adecuado:
- "line" — datos temporales/tendencias (fecha en eje X)
- "bar" — comparacion entre categorias discretas
- "pie" — proporciones/distribuciones (maximo 8 categorias)
- "table" — datos tabulares detallados, KPIs, o muchas columnas
- "histogram" — distribucion de valores numericos continuos
- "area" — tendencias acumuladas o series de tiempo con volumen
Si el usuario pide explicitamente un tipo de grafica, RESPETA su eleccion siempre.

=== FUNCIONES DISPONIBLES ===
IMPORTANTE: Solo puedes usar estas funciones exactas. No inventes otras.

1. "summary" — Resumen ejecutivo con KPIs principales
2. "fallback_rate" — Tasa de fallback del bot
3. "messages_by_direction" — Distribucion Inbound/Bot/Agent
4. "messages_by_hour" — Volumen por hora del dia
5. "messages_over_time" — Tendencia diaria
6. "messages_by_day_of_week" — Volumen por dia de semana
7. "top_contacts" — Top 10 contactos mas activos
8. "intent_distribution" — Intenciones mas comunes
9. "agent_performance" — Rendimiento de agentes humanos
10. "entity_comparison" — Comparacion entre entidades/cooperativas
11. "high_messages_day" — Clientes con mas de 4 mensajes en un dia
12. "high_messages_week" — Clientes con mas de 4 mensajes en una semana
13. "high_messages_month" — Clientes con mas de 4 mensajes en un mes

=== REGLAS PARA SQL ===
- Solo SELECT (no INSERT, UPDATE, DELETE, DROP, etc.)
- Tablas core (esquema public): messages, contacts, agents, daily_stats, chat_conversations, campaigns, toques_daily, toques_heatmap
- Tablas analytics (esquema public_analytics): public_analytics.fact_message_events, public_analytics.dim_date, public_analytics.dim_time, public_analytics.dim_channel, public_analytics.dim_event_type, public_analytics.dim_contact, public_analytics.dim_agent, public_analytics.dim_campaign, public_analytics.dim_conversation
- SIEMPRE usar prefijo public_analytics. para tablas del star schema
- SIEMPRE incluir WHERE tenant_id = '{{TENANT_ID}}'
- SIEMPRE incluir LIMIT (maximo 1000)
- Usa aggregate functions cuando sea posible
- Prefiere funciones pre-built antes de SQL
- Nombra las columnas con alias legibles en espanol cuando sea posible (ej: AS "Fecha", AS "Total Mensajes")

=== REGLAS GENERALES ===
1. Si la pregunta encaja en una funcion pre-built, usala (tipo "analytics")
2. Solo usa "sql" para preguntas que NO cubren las funciones pre-built
3. Si no estas seguro que funcion usar, usa "summary"
4. SIEMPRE agrega un insight de negocio en explanation
5. Responde en espanol, profesional pero accesible
6. Si la pregunta es ambigua o le falta contexto, usa "clarification" para pedir mas informacion antes de ejecutar
"""

    def _get_system_prompt_openai(self) -> str:
        """Simplified system prompt for OpenAI function calling."""
        schema_desc = self.data_service.get_schema_description()
        return f"""Eres un analista de datos senior para VISIONAMOS (cooperativas financieras, Colombia). Canal principal: WhatsApp.

=== PERSONALIDAD ===
- Analitico, conciso, directo. Cero relleno ni parrafos explicativos.
- Cada respuesta EMPIEZA con el hallazgo concreto (cifra exacta, dato principal).
- NUNCA digas "esto es util porque..." ni "es importante saber que...". Solo el dato.
- Si hay anomalia o patron interesante, mencionalo en 1 oracion.
- Maximo 3-4 oraciones por respuesta. Tono profesional, espanol colombiano.

{schema_desc}

=== CONTEXTO DE NEGOCIO ===
- Cliente: VISIONAMOS (red de cooperativas financieras)
- Canal principal: WhatsApp (bot + contact center humano)
- Datos: mensajes, conversaciones, contactos, agentes, estadisticas diarias
- Periodo: datos historicos de 3 meses

=== INSTRUCCIONES ===
- Para preguntas conversacionales (saludos, ayuda), responde directamente sin herramientas
- Para analisis de datos, usa execute_analytics si hay una funcion pre-built que aplique
- Para consultas complejas no cubiertas, usa execute_sql con SQL seguro (solo SELECT)
- Si la pregunta es ambigua, usa ask_clarification
- Prefiere funciones pre-built sobre SQL ad-hoc cuando sea posible
- En SQL: SIEMPRE incluir WHERE tenant_id = '{{TENANT_ID}}' y LIMIT

=== REGLAS SQL ===
- Solo SELECT. Tablas core: messages, contacts, agents, daily_stats, chat_conversations, campaigns, toques_daily, toques_heatmap
- Tablas analytics: public_analytics.fact_message_events, public_analytics.dim_date, etc.
- Alias legibles en espanol (AS "Fecha", AS "Total Mensajes")
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
        """Process a natural language query using AI or demo mode fallback."""
        try:
            return self._process_query_inner(user_question, conversation_history, tenant_filter)
        except Exception as e:
            logger.error("Unexpected error in process_query: %s", e)
            return self._friendly_error(
                "Ocurrio un error inesperado procesando tu consulta. "
                "Por favor intenta reformular tu pregunta o intenta de nuevo en unos momentos."
            )

    def _process_query_inner(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Pre-check for "high messages" queries (deterministic, no LLM needed)
        question_lower = user_question.lower()
        high_msg_indicators = [
            "mas de 4", "mas de 4", "recibieron mas de",
            "recibieron mas de", "mayor a 4", "superiores a 4",
        ]
        if any(ind in question_lower for ind in high_msg_indicators):
            return self._handle_high_messages(question_lower, tenant_filter)

        # OpenAI GPT-4o with function calling (primary)
        if self.openai_client is not None:
            result = self._openai_query(user_question, conversation_history, tenant_filter)
            if result is not None:
                return result

        # Anthropic Claude (secondary)
        if self.client is not None:
            result = self._ai_query(user_question, conversation_history, tenant_filter)
            if result is not None:
                return result

        # No AI provider available — use demo mode as last resort
        logger.warning("No AI provider available, falling back to demo mode")
        return self._demo_mode_query(user_question, tenant_filter)

    # ------------------------------------------------------------------
    # AI query (Claude Sonnet)
    # ------------------------------------------------------------------

    def _ai_query(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            # Build conversation messages
            messages = []
            if conversation_history:
                for msg in conversation_history[-8:]:
                    if msg.get("role") in ("user", "assistant"):
                        messages.append({
                            "role": msg["role"],
                            "content": msg.get("content", ""),
                        })
            messages.append({"role": "user", "content": user_question})

            # Call Anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                system=self._get_system_prompt(),
                messages=messages,
            )

            response_text = response.content[0].text

            # Parse JSON from response
            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group())
                else:
                    return None

            resp_type = response_json.get("type", "conversation")

            # --- Conversation ---
            if resp_type == "conversation":
                return {
                    "type": "conversation",
                    "response": response_json.get("response", ""),
                    "data": None,
                    "chart_type": None,
                    "query_details": None,
                }

            # --- Clarification ---
            if resp_type == "clarification":
                return {
                    "type": "conversation",
                    "response": response_json.get("response", ""),
                    "data": None,
                    "chart_type": None,
                    "query_details": None,
                }

            # --- Analytics (pre-built function) ---
            if resp_type == "analytics":
                function_name = response_json.get("function", "summary")
                explanation = response_json.get("explanation", "")
                result = self._execute_function(function_name, tenant_filter)
                row_count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0
                return {
                    "type": "analytics",
                    "response": explanation,
                    "data": result["data"],
                    "chart_type": result["chart_type"],
                    "query_details": {"function": function_name, "rows_returned": row_count},
                }

            # --- SQL (guarded ad-hoc query) ---
            if resp_type == "sql":
                raw_sql = response_json.get("query", "")
                explanation = response_json.get("explanation", "")
                ai_chart = response_json.get("chart_type")
                ai_title = response_json.get("title")
                return self._execute_guarded_sql(
                    raw_sql, explanation, tenant_filter,
                    chart_type=ai_chart, title=ai_title,
                )

            # Unrecognized type
            return None

        except anthropic.AuthenticationError:
            logger.warning("Anthropic authentication failed")
            return self._friendly_error(
                "Hay un problema con la configuracion del servicio de IA. "
                "Por favor contacta al administrador."
            )
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit reached")
            return self._friendly_error(
                "El servicio de IA esta temporalmente ocupado. "
                "Por favor intenta de nuevo en unos segundos."
            )
        except anthropic.APIConnectionError:
            logger.warning("Anthropic connection failed")
            return self._friendly_error(
                "No se pudo conectar con el servicio de IA. "
                "Verifica tu conexion a internet e intenta de nuevo."
            )
        except anthropic.APIError as e:
            logger.warning("Anthropic API error: %s", e)
            return None
        except Exception as e:
            logger.warning("AI query failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # OpenAI with function calling (GPT-4o)
    # ------------------------------------------------------------------

    def _openai_query(
        self,
        user_question: str,
        conversation_history: List[Dict] = None,
        tenant_filter: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process query via OpenAI GPT-4o with native function calling."""
        try:
            messages = [{"role": "system", "content": self._get_system_prompt_openai()}]
            if conversation_history:
                for msg in conversation_history[-8:]:
                    if msg.get("role") in ("user", "assistant"):
                        messages.append({
                            "role": msg["role"],
                            "content": msg.get("content", ""),
                        })
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

            # If the model responds with tool calls, process them
            if message.tool_calls:
                return self._handle_tool_calls(message.tool_calls, tenant_filter)

            # If the model responds with plain text (conversation/greeting)
            if message.content:
                return {
                    "type": "conversation",
                    "response": message.content,
                    "data": None,
                    "chart_type": None,
                    "query_details": None,
                }

            return None

        except openai.AuthenticationError:
            logger.warning("OpenAI authentication failed")
            return self._friendly_error(
                "Hay un problema con la configuracion del servicio de IA. "
                "Por favor contacta al administrador."
            )
        except openai.RateLimitError:
            logger.warning("OpenAI rate limit reached")
            return self._friendly_error(
                "El servicio de IA esta temporalmente ocupado. "
                "Por favor intenta de nuevo en unos segundos."
            )
        except openai.APIConnectionError:
            logger.warning("OpenAI connection failed")
            return self._friendly_error(
                "No se pudo conectar con el servicio de IA. "
                "Verifica tu conexion a internet e intenta de nuevo."
            )
        except Exception as e:
            logger.error("OpenAI query failed: %s", e)
            return self._friendly_error(
                f"Ocurrio un error con el servicio de IA: {str(e)[:150]}. "
                "Por favor intenta de nuevo."
            )

    def _handle_tool_calls(
        self,
        tool_calls,
        tenant_filter: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Process OpenAI function calling tool_calls."""
        # Process the first tool call (we only expect one per turn)
        tool_call = tool_calls[0]
        func_name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logger.warning("Failed to parse tool call arguments: %s", tool_call.function.arguments)
            return None

        if func_name == "execute_analytics":
            function_name = args.get("function_name", "summary")
            explanation = args.get("explanation", "")
            result = self._execute_function(function_name, tenant_filter)
            row_count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0
            return {
                "type": "analytics",
                "response": explanation,
                "data": result["data"],
                "chart_type": result["chart_type"],
                "query_details": {"function": function_name, "rows_returned": row_count},
            }

        if func_name == "execute_sql":
            raw_sql = args.get("query", "")
            explanation = args.get("explanation", "")
            chart_type = args.get("chart_type")
            title = args.get("title")
            return self._execute_guarded_sql(
                raw_sql, explanation, tenant_filter,
                chart_type=chart_type, title=title,
            )

        if func_name == "ask_clarification":
            question = args.get("question", "")
            return {
                "type": "conversation",
                "response": question,
                "data": None,
                "chart_type": None,
                "query_details": None,
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
        """Execute AI-generated SQL with safety guardrails."""

        sql = raw_sql.strip().rstrip(";")

        # 1. Must be a SELECT
        if not sql.upper().startswith("SELECT"):
            return self._sql_error("Solo se permiten consultas SELECT.")

        # 2. Keyword blocklist
        if SQL_BLOCKLIST.search(sql):
            return self._sql_error("La consulta contiene operaciones no permitidas.")

        # 3. Only allowed tables
        table_pattern = re.compile(
            r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE
        )
        referenced_tables = {m.lower() for m in table_pattern.findall(sql)}
        disallowed = referenced_tables - ALLOWED_TABLES
        if disallowed:
            return self._sql_error(
                f"Tablas no permitidas: {', '.join(disallowed)}. "
                f"Tablas disponibles: {', '.join(sorted(ALLOWED_TABLES))}"
            )

        # 4. Inject tenant_id if not present
        tenant = tenant_filter or settings.DEFAULT_TENANT
        sql = sql.replace("{TENANT_ID}", tenant)
        if "tenant_id" not in sql.lower():
            if " WHERE " in sql.upper():
                sql = re.sub(
                    r"(?i)\bWHERE\b",
                    f"WHERE tenant_id = '{tenant}' AND",
                    sql,
                    count=1,
                )
            else:
                sql = re.sub(
                    r"(?i)(FROM\s+[a-zA-Z_][a-zA-Z0-9_.]*)",
                    rf"\1 WHERE tenant_id = '{tenant}'",
                    sql,
                    count=1,
                )

        # 5. Enforce LIMIT
        if "LIMIT" not in sql.upper():
            sql += f" LIMIT {MAX_SQL_ROWS}"

        # 6. Execute with timeout
        try:
            with engine.connect() as conn:
                conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))
                df = pd.read_sql(text(sql), conn)

            row_count = len(df)
            resolved_chart = chart_type or self._auto_detect_chart_type(df)
            return {
                "type": "analytics",
                "response": explanation,
                "data": df,
                "chart_type": resolved_chart,
                "query_details": {
                    "function": "sql_query",
                    "sql": sql,
                    "rows_returned": row_count,
                    "title": title,
                },
            }

        except Exception as e:
            logger.warning("SQL execution failed: %s — Query: %s", e, sql)
            return self._sql_error(f"Error ejecutando la consulta: {str(e)[:200]}")

    @staticmethod
    def _auto_detect_chart_type(df: pd.DataFrame) -> str:
        """Auto-detect best chart type from DataFrame shape and content."""
        if df.empty or len(df.columns) < 2:
            return "table"
        x_col = df.columns[0]
        x_lower = x_col.lower()
        n_rows = len(df)
        if any(kw in x_lower for kw in ["date", "fecha", "time", "dia", "mes", "month", "week"]):
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
            "data": None,
            "chart_type": None,
            "query_details": None,
        }

    # ------------------------------------------------------------------
    # Pre-built function execution
    # ------------------------------------------------------------------

    def _execute_function(self, function_name: str, tenant_filter: Optional[str]) -> Dict[str, Any]:
        """Execute a pre-built analytics function by name."""

        if function_name == "summary":
            stats = self.data_service.get_summary_stats(tenant_filter)
            fallback = self.data_service.get_fallback_rate(tenant_filter)
            df = pd.DataFrame([
                {"Metrica": "Total Mensajes", "Valor": f"{stats['total_messages']:,}"},
                {"Metrica": "Contactos Unicos", "Valor": f"{stats['unique_contacts']:,}"},
                {"Metrica": "Conversaciones", "Valor": f"{stats['total_conversations']:,}"},
                {"Metrica": "Agentes Activos", "Valor": f"{stats['active_agents']}"},
                {"Metrica": "Tasa de Fallback", "Valor": f"{fallback['rate']}%"},
            ])
            return {"data": df, "chart_type": "table"}

        elif function_name == "fallback_rate":
            stats = self.data_service.get_fallback_rate(tenant_filter)
            status = "Saludable" if stats["rate"] < 15 else "Necesita atencion"
            df = pd.DataFrame([{
                "Metrica": "Tasa de Fallback",
                "Total Mensajes": f"{stats['total']:,}",
                "Mensajes Fallback": f"{stats['fallback_count']:,}",
                "Porcentaje": f"{stats['rate']}%",
                "Estado": status,
            }])
            return {"data": df, "chart_type": "table"}

        elif function_name == "messages_by_direction":
            return {"data": self.data_service.get_messages_by_direction(tenant_filter), "chart_type": "pie"}

        elif function_name == "messages_by_hour":
            return {"data": self.data_service.get_messages_by_hour(tenant_filter), "chart_type": "bar"}

        elif function_name == "messages_over_time":
            return {"data": self.data_service.get_messages_over_time(tenant_filter), "chart_type": "line"}

        elif function_name == "messages_by_day_of_week":
            return {"data": self.data_service.get_messages_by_day_of_week(tenant_filter), "chart_type": "bar"}

        elif function_name == "top_contacts":
            return {"data": self.data_service.get_top_contacts(tenant_filter, limit=10), "chart_type": "bar"}

        elif function_name == "intent_distribution":
            return {"data": self.data_service.get_intent_distribution(tenant_filter, limit=10), "chart_type": "bar"}

        elif function_name == "agent_performance":
            return {"data": self.data_service.get_agent_performance(tenant_filter), "chart_type": "bar"}

        elif function_name == "entity_comparison":
            messages_df = self.data_service.get_messages_dataframe(tenant_filter)
            if not messages_df.empty and "tenant_id" in messages_df.columns:
                df = messages_df.groupby("tenant_id").size().reset_index(name="count")
                df = df.sort_values("count", ascending=False).head(15)
            else:
                df = pd.DataFrame(columns=["tenant_id", "count"])
            return {"data": df, "chart_type": "bar"}

        elif function_name == "high_messages_day":
            return {"data": self.data_service.get_customers_with_high_messages("day", 4, tenant_filter), "chart_type": "table"}

        elif function_name == "high_messages_week":
            return {"data": self.data_service.get_customers_with_high_messages("week", 4, tenant_filter), "chart_type": "table"}

        elif function_name == "high_messages_month":
            return {"data": self.data_service.get_customers_with_high_messages("month", 4, tenant_filter), "chart_type": "table"}

        else:
            return self._execute_function("summary", tenant_filter)

    # ------------------------------------------------------------------
    # High-messages shortcut (deterministic, no LLM)
    # ------------------------------------------------------------------

    def _handle_high_messages(self, question_lower: str, tenant_filter: Optional[str]) -> Dict[str, Any]:
        if any(p in question_lower for p in ["semana", "semanal", "weekly", "7 dias", "7 dias"]):
            func_name, period_text = "high_messages_week", "por semana"
        elif any(p in question_lower for p in ["mes", "mensual", "monthly", "30 dias", "30 dias"]):
            func_name, period_text = "high_messages_month", "por mes"
        else:
            func_name, period_text = "high_messages_day", "por dia"

        result = self._execute_function(func_name, tenant_filter)
        count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0

        return {
            "type": "analytics",
            "response": (
                f"Encontre {count:,} registros de clientes que recibieron mas de 4 mensajes "
                f"{period_text}. Estos clientes pueden requerir atencion especial."
            ),
            "data": result["data"],
            "chart_type": result["chart_type"],
            "query_details": {"function": func_name, "rows_returned": count},
        }

    # ------------------------------------------------------------------
    # Demo mode (keyword matching fallback, no API key needed)
    # ------------------------------------------------------------------

    def _demo_mode_query(self, question: str, tenant_filter: Optional[str]) -> Dict[str, Any]:
        """Pattern match without API — used when no Anthropic key is configured."""
        q = question.lower().strip()

        greetings = ["hola", "hello", "hi", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal"]
        if any(q.startswith(g) or q == g for g in greetings):
            return {
                "type": "conversation",
                "response": (
                    "Hola! Soy tu asistente de analitica. Puedo ayudarte a:\n\n"
                    "- Ver el rendimiento del bot (fallback)\n"
                    "- Analizar horarios pico\n"
                    "- Revisar agentes y contactos\n"
                    "- Comparar entidades\n\n"
                    "Que te gustaria analizar?"
                ),
                "data": None, "chart_type": None, "query_details": None,
            }

        if any(t in q for t in ["gracias", "thanks", "thank you"]):
            return {
                "type": "conversation",
                "response": "Con gusto! Si necesitas mas analisis, aqui estoy.",
                "data": None, "chart_type": None, "query_details": None,
            }

        if any(g in q for g in ["adios", "bye", "chao", "hasta luego"]):
            return {
                "type": "conversation",
                "response": "Hasta luego! Vuelve cuando necesites revisar las metricas.",
                "data": None, "chart_type": None, "query_details": None,
            }

        if any(h in q for h in ["ayuda", "help", "que puedes", "que haces"]):
            return {
                "type": "conversation",
                "response": (
                    "Puedo ayudarte con:\n\n"
                    "- **Bot:** \"Como esta el fallback?\"\n"
                    "- **Horarios:** \"Cual es el horario pico?\"\n"
                    "- **Agentes:** \"Rendimiento de agentes\"\n"
                    "- **Contactos:** \"Top 10 contactos\"\n"
                    "- **Tendencias:** \"Muestra la tendencia\"\n"
                    "- **Entidades:** \"Comparar entidades\"\n"
                    "- **Resumen:** \"Dame un resumen\""
                ),
                "data": None, "chart_type": None, "query_details": None,
            }

        patterns = [
            (["fallback", "fallo", "entiende", "calidad bot"], "fallback_rate",
             "Aqui tienes la tasa de fallback del bot. Un valor menor a 15% es saludable."),
            (["intent", "intencion", "tema", "motivo"], "intent_distribution",
             "Distribucion de intenciones detectadas por el bot. Revela que necesitan los usuarios."),
            (["canal", "direccion", "inbound", "tipo de mensaje"], "messages_by_direction",
             "Distribucion de mensajes por tipo: Inbound (usuario), Bot, Agente humano y Sistema."),
            (["hora", "horario", "pico", "trafico"], "messages_by_hour",
             "Volumen de mensajes por hora del dia. Los picos revelan los horarios de mayor demanda."),
            (["tendencia", "tiempo", "historico", "evolucion", "crecimiento"], "messages_over_time",
             "Tendencia diaria de mensajes. Permite identificar patrones de crecimiento o caida."),
            (["top", "contacto", "activo", "frecuente", "mas mensaje", "mayor mensaje",
              "mas activo", "mayor volumen"], "top_contacts",
             "Los 10 contactos mas activos por volumen de mensajes."),
            (["agente", "operador", "rendimiento", "equipo", "asesor"], "agent_performance",
             "Rendimiento de agentes humanos: mensajes atendidos y conversaciones manejadas."),
            (["semana", "lunes", "martes", "viernes", "sabado", "dia de la semana",
              "dia semana", "dia con mas", "dia mas"], "messages_by_day_of_week",
             "Actividad por dia de la semana. Util para planificar turnos y capacidad."),
            (["cooperativa", "entidad", "comparar", "organizacion"], "entity_comparison",
             "Comparacion de volumen entre entidades/cooperativas."),
            (["distribucion"], "messages_by_direction",
             "Distribucion de mensajes por tipo: Inbound (usuario), Bot, Agente humano y Sistema."),
            (["bot", "automatizacion", "chatbot", "robot"], "fallback_rate",
             "Aqui tienes la tasa de fallback del bot. Un valor menor a 15% es saludable."),
            (["mensaje", "volumen", "cantidad"], "messages_over_time",
             "Tendencia diaria de mensajes. Permite identificar patrones y volumen."),
            (["resumen", "total", "cuantos", "estadistica", "general", "summary",
              "dashboard", "kpi", "metricas"], "summary",
             "Resumen ejecutivo con las metricas principales de la operacion."),
        ]

        for keywords, func_name, explanation in patterns:
            if any(kw in q for kw in keywords):
                result = self._execute_function(func_name, tenant_filter)
                row_count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0
                return {
                    "type": "analytics",
                    "response": explanation,
                    "data": result["data"],
                    "chart_type": result["chart_type"],
                    "query_details": {"function": func_name, "rows_returned": row_count},
                }

        return {
            "type": "conversation",
            "response": (
                "No reconozco esa consulta. Intenta preguntar sobre:\n\n"
                "- Resumen general\n"
                "- Tasa de fallback\n"
                "- Mensajes por hora\n"
                "- Tendencia de mensajes\n"
                "- Top contactos\n"
                "- Rendimiento de agentes\n"
                "- Comparacion de entidades"
            ),
            "data": None, "chart_type": None, "query_details": None,
        }

    # ------------------------------------------------------------------
    # Suggested questions
    # ------------------------------------------------------------------

    @staticmethod
    def get_suggested_questions() -> List[str]:
        return [
            "Dame un resumen general de los datos",
            "Cual es la tasa de fallback?",
            "Mensajes por hora del dia",
            "Top 10 contactos mas activos",
            "Rendimiento de agentes",
            "Comparacion entre entidades",
            "Distribucion de intenciones",
            "Mensajes por dia de la semana",
            "Tendencia de mensajes en el tiempo",
        ]
