"""
AI Agent Service — Hybrid architecture: pre-built functions + guarded SQL fallback.
Uses Anthropic Claude Sonnet for intent classification and SQL generation.
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

# --- SQL Guardrails ---

ALLOWED_TABLES = frozenset({
    "messages", "contacts", "agents", "daily_stats",
    "toques_daily", "campaigns", "toques_heatmap", "toques_usuario",
})

SQL_BLOCKLIST = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|DO|CALL|SET\s+ROLE|pg_sleep|dblink)\b",
    re.IGNORECASE,
)

MAX_SQL_ROWS = 1000
SQL_TIMEOUT_MS = 10_000  # 10 seconds


class AIAgent:
    """AI Agent for natural language query processing with pre-built analytics."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.client = None
        self.model = "claude-sonnet-4-5-20250929"

        if ANTHROPIC_AVAILABLE and settings.has_ai_key:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def is_available(self) -> bool:
        """Check if AI agent is available (API key configured)."""
        return self.client is not None

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        schema_desc = self.data_service.get_schema_description()
        return f"""Eres un analista de datos senior especializado en WhatsApp Business y campañas de comunicación. Trabajas en una plataforma de analytics con asistente de IA.

=== TU PERSONALIDAD ===
- Profesional, amigable y proactivo
- Das insights de negocio, no solo datos
- Respondes en español naturalmente
- Cuando muestras datos, SIEMPRE agregas interpretación

{schema_desc}

=== CLASIFICACIÓN ===
Clasifica cada mensaje en UNA de estas categorías:

1. CONVERSATION — Saludos, despedidas, agradecimientos, preguntas sobre ti
2. ANALYTICS — Preguntas sobre datos que requieren una función de análisis
3. SQL — Preguntas complejas que NO cubren las funciones pre-built

=== FORMATO DE RESPUESTA ===
SIEMPRE responde con JSON válido. Sin texto fuera del JSON.

Para CONVERSATION:
{{"type": "conversation", "response": "Tu respuesta amigable"}}

Para ANALYTICS (funciones pre-built):
{{"type": "analytics", "function": "NOMBRE_DE_FUNCION", "explanation": "Explicación con insight de negocio"}}

Para SQL (consultas ad-hoc):
{{"type": "sql", "query": "SELECT ... FROM ... WHERE tenant_id = '{{TENANT_ID}}' ...", "explanation": "Qué muestra esta consulta"}}

=== FUNCIONES DISPONIBLES ===
IMPORTANTE: Solo puedes usar estas funciones exactas. No inventes otras.

1. "summary" — Resumen ejecutivo con KPIs principales
2. "fallback_rate" — Tasa de fallback del bot
3. "messages_by_direction" — Distribución Inbound/Bot/Agent
4. "messages_by_hour" — Volumen por hora del día
5. "messages_over_time" — Tendencia diaria
6. "messages_by_day_of_week" — Volumen por día de semana
7. "top_contacts" — Top 10 contactos más activos
8. "intent_distribution" — Intenciones más comunes
9. "agent_performance" — Rendimiento de agentes humanos
10. "entity_comparison" — Comparación entre entidades/cooperativas
11. "high_messages_day" — Clientes con más de 4 mensajes en un día
12. "high_messages_week" — Clientes con más de 4 mensajes en una semana
13. "high_messages_month" — Clientes con más de 4 mensajes en un mes

=== REGLAS PARA SQL ===
- Solo SELECT (no INSERT, UPDATE, DELETE, DROP, etc.)
- Solo estas tablas: {', '.join(sorted(ALLOWED_TABLES))}
- SIEMPRE incluir WHERE tenant_id = '{{TENANT_ID}}'
- SIEMPRE incluir LIMIT (máximo 1000)
- Usa aggregate functions cuando sea posible
- Prefiere funciones pre-built antes de SQL

=== REGLAS GENERALES ===
1. Si la pregunta encaja en una función pre-built, úsala (tipo "analytics")
2. Solo usa "sql" para preguntas que NO cubren las funciones pre-built
3. Si no estás seguro qué función usar, usa "summary"
4. SIEMPRE agrega un insight de negocio en explanation
5. Responde en español, profesional pero accesible
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

        # Pre-check for "high messages" queries (deterministic, no LLM needed)
        question_lower = user_question.lower()
        high_msg_indicators = [
            "mas de 4", "más de 4", "recibieron mas de",
            "recibieron más de", "mayor a 4", "superiores a 4",
        ]
        if any(ind in question_lower for ind in high_msg_indicators):
            return self._handle_high_messages(question_lower, tenant_filter)

        # AI mode
        if self.is_available():
            return self._ai_query(user_question, conversation_history, tenant_filter)

        # Demo mode (keyword matching)
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
                for msg in conversation_history[-4:]:
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
                    return self._demo_mode_query(user_question, tenant_filter)

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
                return self._execute_guarded_sql(raw_sql, explanation, tenant_filter)

            # Fallback
            return self._demo_mode_query(user_question, tenant_filter)

        except anthropic.APIError as e:
            logger.warning("Anthropic API error: %s", e)
            return {
                "type": "error",
                "response": f"El servicio de IA no está disponible temporalmente. Error: {e.message}",
                "data": None,
                "chart_type": None,
                "query_details": None,
            }
        except Exception as e:
            logger.exception("AI query failed")
            return {
                "type": "error",
                "response": f"Hubo un problema: {str(e)}. Intenta reformular tu pregunta.",
                "data": None,
                "chart_type": None,
                "query_details": None,
            }

    # ------------------------------------------------------------------
    # Guarded SQL execution (Task 4.2)
    # ------------------------------------------------------------------

    def _execute_guarded_sql(
        self,
        raw_sql: str,
        explanation: str,
        tenant_filter: Optional[str] = None,
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
        # Extract table names from FROM and JOIN clauses
        table_pattern = re.compile(
            r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE
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
            # Inject WHERE tenant_id clause
            if " WHERE " in sql.upper():
                sql = re.sub(
                    r"(?i)\bWHERE\b",
                    f"WHERE tenant_id = '{tenant}' AND",
                    sql,
                    count=1,
                )
            else:
                # Find FROM clause and add WHERE after table name
                sql = re.sub(
                    r"(?i)(FROM\s+[a-zA-Z_][a-zA-Z0-9_]*)",
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
            return {
                "type": "analytics",
                "response": explanation,
                "data": df,
                "chart_type": "table",
                "query_details": {
                    "function": "sql_query",
                    "sql": sql,
                    "rows_returned": row_count,
                },
            }

        except Exception as e:
            logger.warning("SQL execution failed: %s — Query: %s", e, sql)
            return self._sql_error(f"Error ejecutando la consulta: {str(e)[:200]}")

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
        if any(p in question_lower for p in ["semana", "semanal", "weekly", "7 dias", "7 días"]):
            func_name, period_text = "high_messages_week", "por semana"
        elif any(p in question_lower for p in ["mes", "mensual", "monthly", "30 dias", "30 días"]):
            func_name, period_text = "high_messages_month", "por mes"
        else:
            func_name, period_text = "high_messages_day", "por día"

        result = self._execute_function(func_name, tenant_filter)
        count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0

        return {
            "type": "analytics",
            "response": (
                f"Encontré {count:,} registros de clientes que recibieron más de 4 mensajes "
                f"{period_text}. Estos clientes pueden requerir atención especial."
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

        # Greetings
        greetings = ["hola", "hello", "hi", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal"]
        if any(q.startswith(g) or q == g for g in greetings):
            return {
                "type": "conversation",
                "response": (
                    "¡Hola! Soy tu asistente de analítica. Puedo ayudarte a:\n\n"
                    "- Ver el rendimiento del bot (fallback)\n"
                    "- Analizar horarios pico\n"
                    "- Revisar agentes y contactos\n"
                    "- Comparar entidades\n\n"
                    "¿Qué te gustaría analizar?"
                ),
                "data": None, "chart_type": None, "query_details": None,
            }

        # Thanks
        if any(t in q for t in ["gracias", "thanks", "thank you"]):
            return {
                "type": "conversation",
                "response": "¡Con gusto! Si necesitas más análisis, aquí estoy.",
                "data": None, "chart_type": None, "query_details": None,
            }

        # Goodbye
        if any(g in q for g in ["adios", "bye", "chao", "hasta luego"]):
            return {
                "type": "conversation",
                "response": "¡Hasta luego! Vuelve cuando necesites revisar las métricas.",
                "data": None, "chart_type": None, "query_details": None,
            }

        # Help
        if any(h in q for h in ["ayuda", "help", "que puedes", "que haces"]):
            return {
                "type": "conversation",
                "response": (
                    "Puedo ayudarte con:\n\n"
                    "- **Bot:** \"¿Cómo está el fallback?\"\n"
                    "- **Horarios:** \"¿Cuál es el horario pico?\"\n"
                    "- **Agentes:** \"Rendimiento de agentes\"\n"
                    "- **Contactos:** \"Top 10 contactos\"\n"
                    "- **Tendencias:** \"Muestra la tendencia\"\n"
                    "- **Entidades:** \"Comparar entidades\"\n"
                    "- **Resumen:** \"Dame un resumen\""
                ),
                "data": None, "chart_type": None, "query_details": None,
            }

        # Keyword → function mapping (order matters)
        patterns = [
            (["fallback", "bot", "fallo", "entiende", "calidad"], "fallback_rate"),
            (["canal", "direccion", "inbound", "distribucion"], "messages_by_direction"),
            (["hora", "horario", "pico", "trafico"], "messages_by_hour"),
            (["tendencia", "tiempo", "historico", "evolucion"], "messages_over_time"),
            (["top", "contacto", "activo", "frecuente", "usuario"], "top_contacts"),
            (["intent", "intencion", "tema", "motivo"], "intent_distribution"),
            (["agente", "operador", "rendimiento", "equipo", "asesor"], "agent_performance"),
            (["semana", "lunes", "martes", "viernes", "sabado"], "messages_by_day_of_week"),
            (["cooperativa", "entidad", "comparar", "organizacion"], "entity_comparison"),
            (["resumen", "total", "cuantos", "estadistica", "general", "summary"], "summary"),
        ]

        for keywords, func_name in patterns:
            if any(kw in q for kw in keywords):
                result = self._execute_function(func_name, tenant_filter)
                row_count = len(result["data"]) if result["data"] is not None and not result["data"].empty else 0
                return {
                    "type": "analytics",
                    "response": result.get("explanation", f"Resultados de {func_name}:"),
                    "data": result["data"],
                    "chart_type": result["chart_type"],
                    "query_details": {"function": func_name, "rows_returned": row_count},
                }

        # Default help
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
                "- Comparación de entidades"
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
            "¿Cuál es la tasa de fallback?",
            "Mensajes por hora del día",
            "Top 10 contactos más activos",
            "Rendimiento de agentes",
            "Comparación entre entidades",
            "Distribución de intenciones",
            "Mensajes por día de la semana",
            "Tendencia de mensajes en el tiempo",
        ]
