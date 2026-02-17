"""
Data Service — Conversations domain queries.
Migrated from Demo CSV reads → SQLAlchemy Core queries.
Returns pd.DataFrame to maintain API compatibility with ChartService.
"""

import pandas as pd
from sqlalchemy import select, func, text, case, and_
from typing import Optional, List, Dict, Any

from app.models.database import engine
from app.models.schemas import Message, Contact, Agent, DailyStat


class DataService:
    """Service for querying conversation analytics data."""

    def _exec(self, stmt) -> pd.DataFrame:
        """Execute a SQLAlchemy statement and return a DataFrame."""
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _tenant_filter(self, table, tenant_id: Optional[str]):
        """Return a tenant WHERE clause, or True (no filter) if None."""
        if tenant_id:
            return table.c.tenant_id == tenant_id
        return True

    # --- Tenant list ---

    def get_entities(self) -> List[str]:
        """Get unique tenant IDs ordered by message volume."""
        stmt = (
            select(Message.tenant_id, func.count().label("cnt"))
            .group_by(Message.tenant_id)
            .order_by(func.count().desc())
            .limit(50)
        )
        df = self._exec(stmt)
        return df["tenant_id"].tolist() if not df.empty else []

    # --- Summary stats ---

    def get_summary_stats(self, tenant_filter: Optional[str] = None) -> Dict[str, Any]:
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        stmt = select(
            func.count().label("total_messages"),
            func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
            func.count(func.distinct(t.c.agent_id)).label("active_agents"),
            func.count(func.distinct(t.c.conversation_id)).label("total_conversations"),
        ).where(w)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        return {
            "total_messages": row.total_messages or 0,
            "unique_contacts": row.unique_contacts or 0,
            "active_agents": row.active_agents or 0,
            "total_conversations": row.total_conversations or 0,
        }

    # --- Recent messages ---

    def get_recent_messages(self, tenant_filter: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t)
            .where(self._tenant_filter(t, tenant_filter))
            .order_by(t.c.timestamp.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    # --- Grouping queries ---

    def get_messages_by_direction(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t.c.direction, func.count().label("count"))
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.direction)
        )
        return self._exec(stmt)

    def get_messages_by_hour(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t.c.hour, func.count().label("count"))
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.hour)
            .order_by(t.c.hour)
        )
        return self._exec(stmt)

    def get_messages_over_time(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t.c.date, func.count().label("count"))
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        return self._exec(stmt)

    def get_messages_by_day_of_week(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        day_order = case(
            (t.c.day_of_week == "Monday", 1),
            (t.c.day_of_week == "Tuesday", 2),
            (t.c.day_of_week == "Wednesday", 3),
            (t.c.day_of_week == "Thursday", 4),
            (t.c.day_of_week == "Friday", 5),
            (t.c.day_of_week == "Saturday", 6),
            (t.c.day_of_week == "Sunday", 7),
            else_=8,
        )
        stmt = (
            select(t.c.day_of_week, func.count().label("count"))
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.day_of_week)
            .order_by(day_order)
        )
        return self._exec(stmt)

    # --- Top-N queries ---

    def get_top_contacts(self, tenant_filter: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t.c.contact_name, func.count().label("message_count"))
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.contact_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_intent_distribution(self, tenant_filter: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(t.c.intent, func.count().label("count"))
            .where(and_(self._tenant_filter(t, tenant_filter), t.c.intent.isnot(None)))
            .group_by(t.c.intent)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_agent_performance(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        stmt = (
            select(
                t.c.agent_id,
                func.count().label("messages"),
                func.count(func.distinct(t.c.conversation_id)).label("conversations"),
            )
            .where(and_(self._tenant_filter(t, tenant_filter), t.c.agent_id.isnot(None)))
            .group_by(t.c.agent_id)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)

    # --- Fallback rate ---

    def get_fallback_rate(self, tenant_filter: Optional[str] = None) -> Dict[str, Any]:
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        stmt = select(
            func.count().label("total"),
            func.count().filter(t.c.is_fallback == True).label("fallback_count"),  # noqa: E712
        ).where(w)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        total = row.total or 0
        fb = row.fallback_count or 0
        return {
            "fallback_count": fb,
            "total": total,
            "rate": round(fb / total * 100, 2) if total > 0 else 0,
        }

    # --- High-message customers ---

    def get_customers_with_high_messages(
        self,
        period: str = "day",
        threshold: int = 4,
        tenant_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        t = Message.__table__

        if period == "week":
            period_expr = func.to_char(t.c.date, "IYYY-\"W\"IW")
            period_label = "Semana"
        elif period == "month":
            period_expr = func.to_char(t.c.date, "YYYY-MM")
            period_label = "Mes"
        else:
            period_expr = func.to_char(t.c.date, "YYYY-MM-DD")
            period_label = "Dia"

        stmt = (
            select(
                t.c.contact_id,
                t.c.contact_name,
                t.c.tenant_id.label("entity"),
                period_expr.label("periodo"),
                func.count().label("message_count"),
            )
            .where(self._tenant_filter(t, tenant_filter))
            .group_by(t.c.contact_id, t.c.contact_name, t.c.tenant_id, period_expr)
            .having(func.count() > threshold)
            .order_by(period_expr.desc(), func.count().desc())
        )
        df = self._exec(stmt)
        if not df.empty:
            df["tipo_periodo"] = period_label
        return df

    # --- Utility ---

    def get_date_range(self) -> Dict[str, Any]:
        t = Message.__table__
        stmt = select(func.min(t.c.date).label("min_date"), func.max(t.c.date).label("max_date"))
        with engine.connect() as conn:
            row = conn.execute(stmt).first()
        return {"min_date": row.min_date, "max_date": row.max_date}

    def get_messages_dataframe(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Message.__table__
        stmt = select(t).where(self._tenant_filter(t, tenant_filter))
        return self._exec(stmt)

    def get_contacts_dataframe(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Contact.__table__
        stmt = select(t).where(self._tenant_filter(t, tenant_filter))
        return self._exec(stmt)

    def get_schema_description(self) -> str:
        """Schema description for the AI agent system prompt."""
        return """
=== CONTEXTO DE NEGOCIO ===

Esta plataforma analiza datos de WhatsApp Business para la Red Coopcentral, una red de cooperativas financieras en Colombia.

TABLA PRINCIPAL: messages
Columnas: message_id, timestamp, date, hour, day_of_week, send_type, direction, content_type, status, contact_name, contact_id, tenant_id, conversation_id, agent_id, close_reason, intent, is_fallback, message_body, is_bot, is_human, wait_time_seconds, handle_time_seconds

TIPOS DE MENSAJE (direction): Inbound, Bot, Agent, Outbound, System
INDICADOR DE FALLBACK (is_fallback): true/false

contacts: contact_id, contact_name, tenant_id, total_messages, first_contact, last_contact, total_conversations
agents: agent_id, total_messages, conversations_handled, avg_handle_time_seconds

METRICAS CLAVE:
1. Tasa de Fallback: COUNT(is_fallback=true) / COUNT(*) * 100 — Meta: < 15%
2. Volumen de mensajes y tendencia diaria
3. Distribucion por canal (Inbound vs Bot vs Agent)
4. Tiempo de espera (wait_time_seconds) — Meta: < 60s
5. Tiempo de atencion (handle_time_seconds) — Meta: < 300s
"""
