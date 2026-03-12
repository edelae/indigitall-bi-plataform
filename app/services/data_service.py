"""
Data Service — Conversations domain queries.
Migrated from Demo CSV reads → SQLAlchemy Core queries.
Returns pd.DataFrame to maintain API compatibility with ChartService.
"""

import pandas as pd
from datetime import date as date_type, timedelta
from sqlalchemy import select, func, text, case, and_
from typing import Optional, List, Dict, Any

from app.models.database import engine
from app.models.schemas import Message, Contact, Agent, DailyStat, SyncState


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
        """Get unique tenant IDs from contacts (or messages if available)."""
        # Try contacts first (populated by transform bridge)
        stmt = (
            select(Contact.tenant_id, func.count().label("cnt"))
            .group_by(Contact.tenant_id)
            .order_by(func.count().desc())
            .limit(50)
        )
        df = self._exec(stmt)
        if not df.empty:
            return df["tenant_id"].tolist()

        # Fallback to messages
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
        """Aggregate KPIs from multiple tables.

        Uses messages table if populated, otherwise falls back to
        contacts + daily_stats + raw agent count from chat_stats.
        """
        with engine.connect() as conn:
            # Check if messages table has data for this tenant
            t = Message.__table__
            w = self._tenant_filter(t, tenant_filter)
            msg_count = conn.execute(
                select(func.count()).select_from(t).where(w)
            ).scalar() or 0

            if msg_count > 0:
                # Original path: derive everything from messages
                row = conn.execute(
                    select(
                        func.count().label("total_messages"),
                        func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
                        func.count(func.distinct(t.c.agent_id)).label("active_agents"),
                        func.count(func.distinct(t.c.conversation_id)).label("total_conversations"),
                    ).where(w)
                ).first()
                return {
                    "total_messages": row.total_messages or 0,
                    "unique_contacts": row.unique_contacts or 0,
                    "active_agents": row.active_agents or 0,
                    "total_conversations": row.total_conversations or 0,
                }

            # Fallback: aggregate from contacts, daily_stats, and raw chat_stats
            ct = Contact.__table__
            cw = self._tenant_filter(ct, tenant_filter)
            unique_contacts = conn.execute(
                select(func.count()).select_from(ct).where(cw)
            ).scalar() or 0

            dt = DailyStat.__table__
            dw = self._tenant_filter(dt, tenant_filter)
            row = conn.execute(
                select(
                    func.coalesce(func.sum(dt.c.total_messages), 0).label("total_messages"),
                    func.coalesce(func.sum(dt.c.conversations), 0).label("conversations"),
                ).where(dw)
            ).first()
            total_messages = row.total_messages or 0
            total_conversations = row.conversations or 0

            # Active agents from raw.raw_chat_stats (latest snapshot)
            active_agents = 0
            try:
                agent_row = conn.execute(text("""
                    SELECT (source_data->'data'->>'activeAgents')::int
                    FROM raw.raw_chat_stats
                    WHERE endpoint LIKE '%/agent/status%'
                    ORDER BY loaded_at DESC LIMIT 1
                """)).first()
                if agent_row:
                    active_agents = agent_row[0] or 0
            except Exception:
                pass

            return {
                "total_messages": total_messages,
                "unique_contacts": unique_contacts,
                "active_agents": active_agents,
                "total_conversations": total_conversations,
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
        """Fallback rate at CONVERSATION level: % of bot conversations that had fallback."""
        sql = text("""
            WITH conv_flags AS (
                SELECT conversation_id,
                       BOOL_OR(is_fallback) AS had_fallback,
                       BOOL_OR(is_bot)      AS had_bot
                FROM messages
                WHERE conversation_id IS NOT NULL
                  AND (:tenant IS NULL OR tenant_id = :tenant)
                GROUP BY conversation_id
            )
            SELECT COUNT(*) FILTER (WHERE had_bot)                    AS bot_conversations,
                   COUNT(*) FILTER (WHERE had_bot AND had_fallback)   AS fallback_conversations
            FROM conv_flags
        """)
        with engine.connect() as conn:
            row = conn.execute(sql, {"tenant": tenant_filter}).first()

        bot_total = row.bot_conversations or 0
        fb = row.fallback_conversations or 0
        return {
            "fallback_count": fb,
            "total": bot_total,
            "rate": round(fb / bot_total * 100, 2) if bot_total > 0 else 0,
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

    # --- Operations dashboard: filtered queries ---

    def get_summary_stats_for_period(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """KPIs for a date range with trend vs. the immediately preceding period."""
        with engine.connect() as conn:
            t = Message.__table__
            w = self._tenant_filter(t, tenant_filter)
            msg_count = conn.execute(
                select(func.count()).select_from(t).where(w)
            ).scalar() or 0

            use_messages = msg_count > 0
            if use_messages and start_date and end_date:
                cur = self._period_kpis_messages(conn, t, w, start_date, end_date)
                delta = (end_date - start_date).days + 1
                prev_end = start_date - timedelta(days=1)
                prev_start = prev_end - timedelta(days=delta - 1)
                prev = self._period_kpis_messages(conn, t, w, prev_start, prev_end)
            else:
                cur = self._period_kpis_daily(conn, tenant_filter, start_date, end_date)
                if start_date and end_date:
                    delta = (end_date - start_date).days + 1
                    prev_end = start_date - timedelta(days=1)
                    prev_start = prev_end - timedelta(days=delta - 1)
                else:
                    prev_start = prev_end = None
                prev = self._period_kpis_daily(conn, tenant_filter, prev_start, prev_end)

        for k, v in prev.items():
            cur[f"prev_{k}"] = v
        return cur

    @staticmethod
    def _period_kpis_messages(conn, t, base_where, start, end):
        f = and_(base_where, t.c.date >= start, t.c.date <= end)
        row = conn.execute(
            select(
                func.count().label("total_messages"),
                func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
                func.count(func.distinct(t.c.conversation_id)).label("conversations"),
                func.avg(t.c.wait_time_seconds).label("avg_wait_seconds"),
            ).where(f)
        ).first()
        # Fallback rate at conversation level
        fb_row = conn.execute(text("""
            WITH conv_flags AS (
                SELECT conversation_id,
                       BOOL_OR(is_fallback) AS had_fallback,
                       BOOL_OR(is_bot)      AS had_bot
                FROM messages
                WHERE conversation_id IS NOT NULL
                  AND date >= :start AND date <= :end
                GROUP BY conversation_id
            )
            SELECT COUNT(*) FILTER (WHERE had_bot)                  AS bot_convs,
                   COUNT(*) FILTER (WHERE had_bot AND had_fallback) AS fb_convs
            FROM conv_flags
        """), {"start": start, "end": end}).first()
        bot_convs = fb_row.bot_convs or 0
        fb_convs = fb_row.fb_convs or 0
        return {
            "total_messages": row.total_messages or 0,
            "unique_contacts": row.unique_contacts or 0,
            "conversations": row.conversations or 0,
            "avg_wait_seconds": round(float(row.avg_wait_seconds or 0), 1),
            "fallback_rate": round(fb_convs / bot_convs * 100, 2) if bot_convs > 0 else 0,
        }

    def _period_kpis_daily(self, conn, tenant_filter, start, end):
        dt = DailyStat.__table__
        dw = self._tenant_filter(dt, tenant_filter)
        if start and end:
            dw = and_(dw, dt.c.date >= start, dt.c.date <= end)
        row = conn.execute(
            select(
                func.coalesce(func.sum(dt.c.total_messages), 0).label("total_messages"),
                func.coalesce(func.sum(dt.c.unique_contacts), 0).label("unique_contacts"),
                func.coalesce(func.sum(dt.c.conversations), 0).label("conversations"),
                func.coalesce(func.sum(dt.c.fallback_count), 0).label("fallback_count"),
            ).where(dw)
        ).first()
        total = row.total_messages or 0
        fb = row.fallback_count or 0
        return {
            "total_messages": total,
            "unique_contacts": row.unique_contacts or 0,
            "conversations": row.conversations or 0,
            "avg_wait_seconds": 0,
            "fallback_rate": round(fb / total * 100, 2) if total > 0 else 0,
        }

    def get_messages_over_time_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Messages per day within a date range (falls back to DailyStat)."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.date, func.count().label("count"))
            .where(w)
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        df = self._exec(stmt)
        if df.empty and start_date and end_date:
            dt = DailyStat.__table__
            dw = self._tenant_filter(dt, tenant_filter)
            dw = and_(dw, dt.c.date >= start_date, dt.c.date <= end_date)
            stmt = (
                select(dt.c.date, dt.c.total_messages.label("count"))
                .where(dw)
                .order_by(dt.c.date)
            )
            df = self._exec(stmt)
        return df

    def get_direction_breakdown_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Messages by direction within a date range."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.direction, func.count().label("count"))
            .where(w)
            .group_by(t.c.direction)
        )
        return self._exec(stmt)

    def get_agent_performance_detailed(
        self, tenant_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """Agent-level metrics (tries dbt mart, then messages, then agents table)."""
        # Try dbt mart first
        try:
            sql = text(
                "SELECT agent_id, total_messages, conversations_handled, "
                "unique_contacts, avg_handle_seconds, avg_wait_seconds, active_days "
                "FROM marts.fct_agent_performance WHERE tenant_id = :tenant"
            )
            with engine.connect() as conn:
                df = pd.read_sql(sql, conn, params={"tenant": tenant_filter})
            if not df.empty:
                return df
        except Exception:
            pass

        # Fallback: aggregate from messages
        t = Message.__table__
        w = and_(self._tenant_filter(t, tenant_filter), t.c.agent_id.isnot(None))
        stmt = (
            select(
                t.c.agent_id,
                func.count().label("total_messages"),
                func.count(func.distinct(t.c.conversation_id)).label("conversations_handled"),
                func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
                func.avg(t.c.handle_time_seconds).label("avg_handle_seconds"),
                func.avg(t.c.wait_time_seconds).label("avg_wait_seconds"),
                func.count(func.distinct(t.c.date)).label("active_days"),
            )
            .where(w)
            .group_by(t.c.agent_id)
            .order_by(func.count().desc())
        )
        df = self._exec(stmt)
        if not df.empty:
            return df

        # Final fallback: agents table
        at = Agent.__table__
        aw = self._tenant_filter(at, tenant_filter)
        stmt = (
            select(
                at.c.agent_id,
                at.c.total_messages,
                at.c.conversations_handled,
            )
            .where(aw)
            .order_by(at.c.total_messages.desc())
        )
        df = self._exec(stmt)
        for col in ["unique_contacts", "avg_handle_seconds", "avg_wait_seconds", "active_days"]:
            if col not in df.columns:
                df[col] = 0
        return df

    # --- Dashboard: additional filtered queries ---

    def get_hourly_distribution_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Message count by hour within a date range."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.hour, func.count().label("count"))
            .where(w)
            .group_by(t.c.hour)
            .order_by(t.c.hour)
        )
        return self._exec(stmt)

    def get_day_of_week_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Message count by day of week within a date range."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
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
            .where(w)
            .group_by(t.c.day_of_week)
            .order_by(day_order)
        )
        df = self._exec(stmt)
        if not df.empty:
            day_map = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
                "Thursday": "Jueves", "Friday": "Viernes",
                "Saturday": "Sabado", "Sunday": "Domingo",
            }
            df["day_of_week"] = df["day_of_week"].map(
                lambda d: day_map.get(d.strip(), d.strip())
            )
        return df

    def get_bot_vs_human_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Conversation classification: Bot-only / Humano-only / Mixta."""
        sql = text("""
            WITH conv_flags AS (
                SELECT conversation_id,
                       BOOL_OR(is_bot)   AS has_bot,
                       BOOL_OR(is_human) AS has_human
                FROM messages
                WHERE conversation_id IS NOT NULL
                  AND (:tenant IS NULL OR tenant_id = :tenant)
                  AND (:start IS NULL OR date >= :start)
                  AND (:end   IS NULL OR date <= :end)
                GROUP BY conversation_id
            )
            SELECT category, COUNT(*) AS count FROM (
                SELECT CASE
                    WHEN has_bot AND NOT has_human THEN 'Bot'
                    WHEN NOT has_bot AND has_human THEN 'Agente'
                    WHEN has_bot AND has_human     THEN 'Mixta'
                    ELSE 'Otro'
                END AS category
                FROM conv_flags
            ) sub
            GROUP BY category
            ORDER BY count DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params={
                "tenant": tenant_filter, "start": start_date, "end": end_date,
            })

    def get_top_intents_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top N intents by message count within a date range."""
        t = Message.__table__
        w = and_(
            self._tenant_filter(t, tenant_filter),
            t.c.intent.isnot(None),
            t.c.intent != "",
        )
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.intent, func.count().label("count"))
            .where(w)
            .group_by(t.c.intent)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_contacts_dataframe(self, tenant_filter: Optional[str] = None) -> pd.DataFrame:
        t = Contact.__table__
        stmt = select(t).where(self._tenant_filter(t, tenant_filter))
        return self._exec(stmt)

    # --- Bot / Automation dashboard queries ---

    def get_fallback_trend_filtered(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily fallback rate at CONVERSATION level."""
        sql = text("""
            WITH conv_flags AS (
                SELECT conversation_id,
                       MIN(date)            AS date,
                       BOOL_OR(is_fallback) AS had_fallback,
                       BOOL_OR(is_bot)      AS had_bot
                FROM messages
                WHERE conversation_id IS NOT NULL
                  AND (:tenant IS NULL OR tenant_id = :tenant)
                  AND (:start IS NULL OR date >= :start)
                  AND (:end   IS NULL OR date <= :end)
                GROUP BY conversation_id
            )
            SELECT date,
                   COUNT(*) FILTER (WHERE had_bot)                  AS total,
                   COUNT(*) FILTER (WHERE had_bot AND had_fallback) AS fallback_count
            FROM conv_flags
            GROUP BY date
            ORDER BY date
        """)
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={
                "tenant": tenant_filter, "start": start_date, "end": end_date,
            })
        if not df.empty:
            df["fallback_rate"] = (df["fallback_count"] / df["total"] * 100).round(2)
            df["fallback_rate"] = df["fallback_rate"].fillna(0)
        return df

    def get_bot_resolution_summary(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Conversation resolution: Bot-only vs Escalada vs Humano-only."""
        sql = text("""
            WITH conv_flags AS (
                SELECT conversation_id,
                       BOOL_OR(is_bot)   AS has_bot,
                       BOOL_OR(is_human) AS has_human
                FROM messages
                WHERE conversation_id IS NOT NULL
                  AND (:tenant IS NULL OR tenant_id = :tenant)
                  AND (:start IS NULL OR date >= :start)
                  AND (:end   IS NULL OR date <= :end)
                GROUP BY conversation_id
            )
            SELECT category, COUNT(*) AS count FROM (
                SELECT CASE
                    WHEN has_bot AND NOT has_human THEN 'Bot'
                    WHEN has_bot AND has_human     THEN 'Escalada'
                    WHEN NOT has_bot AND has_human THEN 'Agente'
                    ELSE 'Otro'
                END AS category
                FROM conv_flags
            ) sub
            GROUP BY category
            ORDER BY count DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params={
                "tenant": tenant_filter, "start": start_date, "end": end_date,
            })

    def get_content_type_breakdown(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Message count by content type."""
        t = Message.__table__
        w = and_(
            self._tenant_filter(t, tenant_filter),
            t.c.content_type.isnot(None),
            t.c.content_type != "",
        )
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.content_type, func.count().label("count"))
            .where(w)
            .group_by(t.c.content_type)
            .order_by(func.count().desc())
            .limit(10)
        )
        return self._exec(stmt)

    # --- Control de Toques dashboard queries ---

    def get_toques_kpis(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        threshold: int = 4,
    ) -> Dict[str, Any]:
        """KPIs: % over-touched, total contacts, avg msgs per contact per week."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)

        week_expr = func.to_char(t.c.date, "IYYY-IW")
        inner = (
            select(
                t.c.contact_id,
                week_expr.label("week"),
                func.count().label("msg_count"),
            )
            .where(w)
            .group_by(t.c.contact_id, week_expr)
            .subquery()
        )

        with engine.connect() as conn:
            total_records = conn.execute(
                select(func.count()).select_from(inner)
            ).scalar() or 0
            over_touched = conn.execute(
                select(func.count()).select_from(inner).where(inner.c.msg_count > threshold)
            ).scalar() or 0
            avg_msgs = conn.execute(
                select(func.avg(inner.c.msg_count))
            ).scalar() or 0

        pct = round(over_touched / total_records * 100, 1) if total_records > 0 else 0
        return {
            "total_contact_weeks": total_records,
            "over_touched": over_touched,
            "pct_over_touched": pct,
            "avg_msgs_per_contact_week": round(float(avg_msgs), 1),
        }

    def get_toques_distribution(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Distribution of messages per contact per week (for histogram)."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)

        week_expr = func.to_char(t.c.date, "IYYY-IW")
        inner = (
            select(
                t.c.contact_id,
                week_expr.label("week"),
                func.count().label("msg_count"),
            )
            .where(w)
            .group_by(t.c.contact_id, week_expr)
            .subquery()
        )

        bucket = case(
            (inner.c.msg_count <= 1, "1"),
            (inner.c.msg_count <= 2, "2"),
            (inner.c.msg_count <= 3, "3"),
            (inner.c.msg_count <= 4, "4"),
            (inner.c.msg_count <= 7, "5-7"),
            (inner.c.msg_count <= 10, "8-10"),
            else_="10+",
        )
        stmt = (
            select(bucket.label("bucket"), func.count().label("count"))
            .group_by(bucket)
        )
        df = self._exec(stmt)
        if not df.empty:
            order = ["1", "2", "3", "4", "5-7", "8-10", "10+"]
            df["bucket"] = pd.Categorical(df["bucket"], categories=order, ordered=True)
            df = df.sort_values("bucket").reset_index(drop=True)
        return df

    def get_toques_weekly_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        threshold: int = 4,
    ) -> pd.DataFrame:
        """Weekly trend of over-touched percentage."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)

        week_expr = func.to_char(t.c.date, "IYYY-IW")
        inner = (
            select(
                t.c.contact_id,
                week_expr.label("week"),
                func.count().label("msg_count"),
            )
            .where(w)
            .group_by(t.c.contact_id, week_expr)
            .subquery()
        )

        stmt = (
            select(
                inner.c.week,
                func.count().label("total_contacts"),
                func.sum(case((inner.c.msg_count > threshold, 1), else_=0)).label("over_touched"),
            )
            .group_by(inner.c.week)
            .order_by(inner.c.week)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["pct_over_touched"] = (df["over_touched"] / df["total_contacts"] * 100).round(1)
        return df

    def get_over_touched_contacts(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        threshold: int = 4,
        limit: int = 100,
    ) -> pd.DataFrame:
        """List of over-touched contacts for table and CSV export."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)

        week_expr = func.to_char(t.c.date, "IYYY-IW")
        stmt = (
            select(
                t.c.contact_id,
                t.c.contact_name,
                week_expr.label("semana"),
                func.count().label("mensajes"),
            )
            .where(w)
            .group_by(t.c.contact_id, t.c.contact_name, week_expr)
            .having(func.count() > threshold)
            .order_by(week_expr.desc(), func.count().desc())
            .limit(limit)
        )
        return self._exec(stmt)

    # --- WhatsApp/Bot dashboard queries ---

    def get_wa_kpis(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """KPIs for WhatsApp/Bot tab — conversation-level bot resolution and fallback."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)

        with engine.connect() as conn:
            # Message-level counts (total messages, contacts, delivery)
            row = conn.execute(
                select(
                    func.count().label("total_messages"),
                    func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
                    func.avg(t.c.wait_time_seconds).label("avg_wait"),
                    func.sum(case((t.c.status.in_(["channel_delivered", "channel_read"]), 1), else_=0)).label("delivered"),
                ).where(w)
            ).first()

            # Conversation-level: bot resolution and fallback
            conv_row = conn.execute(text("""
                WITH conv_flags AS (
                    SELECT conversation_id,
                           BOOL_OR(is_bot)      AS has_bot,
                           BOOL_OR(is_human)     AS has_human,
                           BOOL_OR(is_fallback)  AS had_fallback
                    FROM messages
                    WHERE conversation_id IS NOT NULL
                      AND (:tenant IS NULL OR tenant_id = :tenant)
                      AND (:start IS NULL OR date >= :start)
                      AND (:end   IS NULL OR date <= :end)
                    GROUP BY conversation_id
                )
                SELECT COUNT(*)                                              AS total_convs,
                       COUNT(*) FILTER (WHERE has_bot AND NOT has_human)     AS bot_resolved,
                       COUNT(*) FILTER (WHERE has_bot)                       AS bot_convs,
                       COUNT(*) FILTER (WHERE has_bot AND had_fallback)      AS fallback_convs
                FROM conv_flags
            """), {"tenant": tenant_filter, "start": start_date, "end": end_date}).first()

        total = row.total_messages or 0
        delivered = row.delivered or 0
        total_convs = conv_row.total_convs or 0
        bot_resolved = conv_row.bot_resolved or 0
        bot_convs = conv_row.bot_convs or 0
        fb_convs = conv_row.fallback_convs or 0
        return {
            "total_messages": total,
            "unique_contacts": row.unique_contacts or 0,
            "fallback_rate": round(fb_convs / bot_convs * 100, 2) if bot_convs > 0 else 0,
            "avg_wait_seconds": round(float(row.avg_wait or 0), 1),
            "delivery_rate": round(delivered / total * 100, 2) if total > 0 else 0,
            "bot_resolution_pct": round(bot_resolved / total_convs * 100, 2) if total_convs > 0 else 0,
        }

    def get_message_status_distribution(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Message count by delivery status."""
        t = Message.__table__
        w = and_(
            self._tenant_filter(t, tenant_filter),
            t.c.status.isnot(None),
            t.c.status != "",
        )
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.status, func.count().label("count"))
            .where(w)
            .group_by(t.c.status)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)

    def get_messages_heatmap(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Hour x Day-of-week heatmap for messages."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(t.c.day_of_week, t.c.hour.label("hora"), func.count().label("value"))
            .where(w)
            .group_by(t.c.day_of_week, t.c.hour)
            .order_by(t.c.hour)
        )
        df = self._exec(stmt)
        if not df.empty:
            day_map = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
                "Thursday": "Jueves", "Friday": "Viernes",
                "Saturday": "Sabado", "Sunday": "Domingo",
            }
            df["dia_semana"] = df["day_of_week"].map(
                lambda d: day_map.get(d.strip(), d.strip())
            )
            df = df[["dia_semana", "hora", "value"]]
        return df

    def get_messages_page(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> pd.DataFrame:
        """Paginated message detail table."""
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        stmt = (
            select(
                t.c.date, t.c.hour, t.c.direction, t.c.content_type,
                t.c.status, t.c.contact_name, t.c.intent, t.c.is_fallback,
            )
            .where(w)
            .order_by(t.c.date.desc(), t.c.hour.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return self._exec(stmt)

    def get_schema_description(self) -> str:
        """Schema description for the AI agent system prompt."""
        return """
=== CONTEXTO DE NEGOCIO ===

Plataforma de analytics para Visionamos (Red Coopcentral), una red de cooperativas financieras en Colombia.
Canal unico: WhatsApp Cloud API. Combina chatbot Dialogflow + agentes humanos + notificaciones del sistema.

=== TABLAS DISPONIBLES ===

TABLA: messages (principal — 131K+ filas)
Columnas: message_id, timestamp, date, hour, day_of_week, send_type, direction, content_type, status, contact_name, contact_id, tenant_id, conversation_id, agent_id, close_reason, intent, is_fallback, message_body, is_bot, is_human, wait_time_seconds, handle_time_seconds
- direction: Inbound (usuario), Bot (dialogflow), Agent (humano), Outbound, System
- send_type: input, operator, dialogflow, agent_notification, note
- is_fallback: true/false — indica si el bot no entendio la intencion
- is_bot/is_human: clasifican el origen del mensaje

TABLA: contacts (1,200+ filas)
Columnas: contact_id, contact_name, tenant_id, total_messages, first_contact, last_contact, total_conversations

TABLA: agents (170+ filas)
Columnas: agent_id, tenant_id, total_messages, conversations_handled, avg_handle_time_seconds

TABLA: daily_stats (85+ filas)
Columnas: tenant_id, date, total_messages, unique_contacts, conversations, fallback_count

TABLA: chat_conversations (60K+ filas — sesiones de agente)
Columnas: session_id, conversation_session_id, contact_id, agent_id, agent_email, channel, queued_at, assigned_at, closed_at, initial_session_id, wait_time_seconds, handle_time_seconds, tenant_id

TABLA: chat_channels (canales de comunicacion)
Columnas: channel_id, channel_type, channel_name, phone_number, status, config, tenant_id

TABLA: chat_topics (categorias de conversacion)
Columnas: topic_id, topic_name, description, is_active, tenant_id

TABLA: nps_surveys (928+ filas — encuestas NPS de satisfaccion)
Columnas: message_date, date, hour, day_of_week, month_label, contact_name, contact_id, entity, score_atencion, score_asesor, rapida, resuelto, volveria, nps_categoria, comentario, agent_id, conversation_id, close_reason, canal_tipo, tenant_id
- score_atencion: calificacion de la atencion (1-5)
- score_asesor: calificacion del asesor (1-5)
- rapida/resuelto/volveria: respuestas binarias (1=si, 0=no)
- nps_categoria: Promotor, Pasivo, Detractor
- entity: nombre de la cooperativa/entidad
- canal_tipo: tipo de canal (ej: WhatsApp)

TABLA: campaigns (campanas de push/comunicacion)
Columnas: campana_id, campana_nombre, canal, proyecto_cuenta, tipo_campana, total_enviados, total_entregados, total_clicks, fecha_inicio, fecha_fin, ctr, tasa_entrega, tenant_id

TABLA: toques_daily (metricas diarias por canal)
Columnas: date, canal, proyecto_cuenta, enviados, entregados, clicks, usuarios_unicos, abiertos, rebotes, ctr, tasa_entrega, tenant_id

TABLA: toques_heatmap (mapa de calor hora/dia)
Columnas: canal, dia_semana, hora, enviados, clicks, abiertos, ctr, dia_orden, tenant_id

TABLA: toques_usuario (toques por usuario)
Columnas: telefono, canal, proyecto_cuenta, total_toques, total_clicks, primer_toque, ultimo_toque, dias_activos, tenant_id

=== TABLAS dbt MARTS (esquema public_marts — datos agregados y dimensionales) ===
IMPORTANTE: Estas tablas estan en el esquema public_marts. Usa el prefijo public_marts. en tus queries.
Ejemplo: SELECT * FROM public_marts.fct_daily_stats WHERE tenant_id = 'visionamos' LIMIT 100

TABLA: public_marts.fct_daily_stats (estadisticas diarias consolidadas)
Columnas: tenant_id, date, total_messages, unique_contacts, conversations, active_agents, fallback_count, fallback_rate, avg_wait_seconds, avg_handle_seconds, total_enviados, total_entregados, total_clicks, total_conversiones, avg_ctr

TABLA: public_marts.fct_messages_daily (detalle diario de mensajes WhatsApp)
Columnas: tenant_id, date, total_messages, unique_contacts, conversations, active_agents, inbound_count, bot_count, agent_count, fallback_count, fallback_rate, avg_wait_seconds, avg_handle_seconds

TABLA: public_marts.fct_agent_performance (rendimiento por agente)
Columnas: tenant_id, agent_id, total_messages, conversations_handled, unique_contacts, active_days, first_active, last_active, avg_handle_seconds, median_handle_seconds, avg_wait_seconds, avg_total_duration_seconds, escalated_fallbacks, closed_conversations

TABLA: public_marts.fct_toques_metrics (metricas de campanas por canal y mes)
Columnas: tenant_id, canal, proyecto_cuenta, month, total_enviados, total_entregados, total_clicks, total_chunks, total_usuarios_unicos, total_abiertos, total_rebotes, total_bloqueados, total_spam, total_desuscritos, total_conversiones, ctr, tasa_entrega, open_rate, conversion_rate, active_days

TABLA: public_marts.dim_campaigns (dimension campanas)
Columnas: tenant_id, campana_id, campana_nombre, canal, proyecto_cuenta, tipo_campana, total_enviados, total_entregados, total_clicks, total_chunks, fecha_inicio, fecha_fin, total_abiertos, total_rebotes, total_bloqueados, total_spam, total_desuscritos, total_conversiones, ctr, tasa_entrega, open_rate, conversion_rate, active_days, first_send_date, last_send_date

TABLA: public_marts.dim_contacts (dimension contactos)
Columnas: tenant_id, contact_id, contact_name, total_messages, total_conversations, first_contact, last_contact, fallback_messages, active_days

NOTA MARTS: Para queries con datos agregados, usa public_marts. Es mas eficiente que consultar tablas raw.
Ejemplo: SELECT date, total_messages, fallback_rate FROM public_marts.fct_daily_stats WHERE tenant_id = 'visionamos' ORDER BY date DESC LIMIT 30

=== METRICAS CLAVE ===
1. Tasa de Fallback: COUNT(is_fallback=true) / COUNT(*) * 100 — Meta: < 15% (actual ~3%)
2. Volumen de mensajes y tendencia diaria — Promedio: 1,440 msgs/dia
3. Distribucion por tipo: Bot vs Agente vs Usuario vs Sistema
4. Tiempo de espera (wait_time_seconds) — Meta: < 60s
5. Tiempo de atencion (handle_time_seconds) — Meta: < 300s
6. Horarios pico: 13:00-22:00 (bi-modal: 15-16h y 19-21h)
7. Dias activos: Lun-Vie (sabado minimo, domingo casi nulo)
"""
