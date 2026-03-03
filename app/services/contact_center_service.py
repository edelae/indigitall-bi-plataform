"""Contact Center Service — Queries for agent conversation analytics."""

import logging

import pandas as pd
from datetime import date as date_type
from sqlalchemy import select, func, and_, case, text
from typing import Optional, Dict, Any

from app.models.database import engine
from app.models.schemas import ChatConversation

log = logging.getLogger(__name__)


class ContactCenterService:
    """Service for querying contact center / chat conversation data."""

    def _exec(self, stmt) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _tenant_filter(self, table, tenant_id: Optional[str]):
        if tenant_id:
            return table.c.tenant_id == tenant_id
        return True

    def _base_where(self, t, tenant, start_date, end_date):
        w = self._tenant_filter(t, tenant)
        if start_date and end_date:
            w = and_(w, func.date(t.c.closed_at) >= start_date, func.date(t.c.closed_at) <= end_date)
        return w

    def get_cc_kpis(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """Contact center KPIs: total convs, active agents, avg wait, avg handle."""
        t = ChatConversation.__table__
        w = self._base_where(t, tenant_filter, start_date, end_date)

        stmt = select(
            func.count().label("total_conversations"),
            func.count(func.distinct(t.c.agent_id)).label("active_agents"),
            func.avg(t.c.wait_time_seconds).label("avg_wait"),
            func.avg(t.c.handle_time_seconds).label("avg_handle"),
        ).where(w)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        return {
            "total_conversations": row.total_conversations or 0,
            "active_agents": row.active_agents or 0,
            "avg_wait_minutes": round(float(row.avg_wait or 0) / 60, 1),
            "avg_handle_minutes": round(float(row.avg_handle or 0) / 60, 1),
        }

    def get_conversations_over_time(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily conversation count."""
        t = ChatConversation.__table__
        w = self._base_where(t, tenant_filter, start_date, end_date)
        date_col = func.date(t.c.closed_at).label("date")
        stmt = (
            select(date_col, func.count().label("count"))
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        return self._exec(stmt)

    def get_conversations_by_agent(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 15,
    ) -> pd.DataFrame:
        """Conversation count per agent."""
        t = ChatConversation.__table__
        w = and_(self._base_where(t, tenant_filter, start_date, end_date), t.c.agent_id.isnot(None))
        stmt = (
            select(
                t.c.agent_id,
                func.count().label("conversations"),
                func.count(func.distinct(t.c.contact_id)).label("contacts"),
            )
            .where(w)
            .group_by(t.c.agent_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_close_reasons(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Conversation count by close reason (derived from messages)."""
        from app.models.schemas import Message
        t = Message.__table__
        w = self._tenant_filter(t, tenant_filter)
        if start_date and end_date:
            w = and_(w, t.c.date >= start_date, t.c.date <= end_date)
        w = and_(w, t.c.close_reason.isnot(None), t.c.close_reason != "")
        stmt = (
            select(t.c.close_reason.label("reason"), func.count().label("count"))
            .where(w)
            .group_by(t.c.close_reason)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)

    def get_wait_time_distribution(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Wait time in buckets (0-1m, 1-5m, 5-15m, 15-30m, 30m+)."""
        t = ChatConversation.__table__
        w = and_(
            self._base_where(t, tenant_filter, start_date, end_date),
            t.c.wait_time_seconds.isnot(None),
        )
        bucket = case(
            (t.c.wait_time_seconds < 60, "0-1 min"),
            (t.c.wait_time_seconds < 300, "1-5 min"),
            (t.c.wait_time_seconds < 900, "5-15 min"),
            (t.c.wait_time_seconds < 1800, "15-30 min"),
            else_="30+ min",
        )
        stmt = (
            select(bucket.label("bucket"), func.count().label("count"))
            .where(w)
            .group_by(bucket)
        )
        df = self._exec(stmt)
        if not df.empty:
            order = ["0-1 min", "1-5 min", "5-15 min", "15-30 min", "30+ min"]
            df["bucket"] = pd.Categorical(df["bucket"], categories=order, ordered=True)
            df = df.sort_values("bucket").reset_index(drop=True)
        return df

    def get_cc_kpis_expanded(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """Expanded KPIs: convs, FCR, avg FRT, avg handle, coverage, NPS placeholder."""
        t = ChatConversation.__table__
        w = self._base_where(t, tenant_filter, start_date, end_date)

        with engine.connect() as conn:
            row = conn.execute(
                select(
                    func.count().label("total_conversations"),
                    func.count(func.distinct(t.c.agent_id)).label("active_agents"),
                    func.avg(t.c.wait_time_seconds).label("avg_frt"),
                    func.avg(t.c.handle_time_seconds).label("avg_handle"),
                    func.count(func.distinct(t.c.contact_id)).label("total_contacts"),
                ).where(w)
            ).first()

            # FCR: contacts with exactly 1 session / total contacts
            fcr_row = conn.execute(
                select(func.count()).select_from(
                    select(t.c.contact_id)
                    .where(and_(w, t.c.contact_id.isnot(None)))
                    .group_by(t.c.contact_id)
                    .having(func.count() == 1)
                    .subquery()
                )
            ).scalar() or 0

        total_contacts = row.total_contacts or 0
        total_convs = row.total_conversations or 0
        return {
            "total_conversations": total_convs,
            "active_agents": row.active_agents or 0,
            "fcr_rate": round(fcr_row / total_contacts * 100, 1) if total_contacts > 0 else 0,
            "avg_frt_seconds": round(float(row.avg_frt or 0), 0),
            "avg_handle_seconds": round(float(row.avg_handle or 0), 0),
            "coverage_rate": 0,
            "nps": 0,
        }

    def get_first_response_time_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily average first response time trend."""
        t = ChatConversation.__table__
        w = and_(
            self._base_where(t, tenant_filter, start_date, end_date),
            t.c.wait_time_seconds.isnot(None),
        )
        date_col = func.date(t.c.closed_at).label("date")
        stmt = (
            select(date_col, func.avg(t.c.wait_time_seconds).label("avg_frt_seconds"))
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        return self._exec(stmt)

    def get_handle_time_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily average handle time trend."""
        t = ChatConversation.__table__
        w = and_(
            self._base_where(t, tenant_filter, start_date, end_date),
            t.c.handle_time_seconds.isnot(None),
        )
        date_col = func.date(t.c.closed_at).label("date")
        stmt = (
            select(date_col, func.avg(t.c.handle_time_seconds).label("avg_handle_seconds"))
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        return self._exec(stmt)

    def get_agent_performance_table(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 20,
    ) -> pd.DataFrame:
        """Expanded agent performance with FRT and handle time."""
        t = ChatConversation.__table__
        w = and_(
            self._base_where(t, tenant_filter, start_date, end_date),
            t.c.agent_id.isnot(None),
        )
        stmt = (
            select(
                t.c.agent_id,
                func.count().label("conversations"),
                func.count(func.distinct(t.c.contact_id)).label("contacts"),
                func.avg(t.c.wait_time_seconds).label("avg_frt"),
                func.avg(t.c.handle_time_seconds).label("avg_handle"),
            )
            .where(w)
            .group_by(t.c.agent_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["avg_frt"] = df["avg_frt"].round(0).fillna(0).astype(int)
            df["avg_handle"] = df["avg_handle"].round(0).fillna(0).astype(int)
        return df

    def get_conversation_drill_data(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        granularity: str = "month",
    ) -> pd.DataFrame:
        """Aggregated conversation counts for drill-down."""
        t = ChatConversation.__table__
        w = self._base_where(t, tenant_filter, start_date, end_date)

        if granularity == "month":
            period = func.to_char(t.c.closed_at, "YYYY-MM").label("period")
        elif granularity == "week":
            period = func.to_char(t.c.closed_at, "IYYY-\"W\"IW").label("period")
        else:
            period = func.date(t.c.closed_at).label("period")

        stmt = (
            select(period, func.count().label("count"))
            .where(w)
            .group_by(period)
            .order_by(period)
        )
        return self._exec(stmt)

    def get_hourly_queue(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Conversations by hour of day (queued_at)."""
        t = ChatConversation.__table__
        w = and_(
            self._base_where(t, tenant_filter, start_date, end_date),
            t.c.queued_at.isnot(None),
        )
        hour_col = func.extract("hour", t.c.queued_at).label("hour")
        stmt = (
            select(hour_col, func.count().label("count"))
            .where(w)
            .group_by(hour_col)
            .order_by(hour_col)
        )
        return self._exec(stmt)

    # ==================== WhatsApp Atendimiento Methods ====================

    def get_conversation_type_counts(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, int]:
        """Classify conversations: bot-only, human-only, or mixed."""
        from app.models.schemas import Message
        m = Message.__table__
        w = self._tenant_filter(m, tenant_filter)
        if start_date and end_date:
            w = and_(w, m.c.date >= start_date, m.c.date <= end_date)

        sub = (
            select(
                m.c.conversation_id,
                func.bool_or(m.c.is_bot).label("has_bot"),
                func.bool_or(m.c.is_human).label("has_human"),
            )
            .where(and_(w, m.c.conversation_id.isnot(None)))
            .group_by(m.c.conversation_id)
            .subquery()
        )

        stmt = select(
            func.count().label("total"),
            func.sum(case((and_(sub.c.has_bot, ~sub.c.has_human), 1), else_=0)).label("bot_only"),
            func.sum(case((and_(~sub.c.has_bot, sub.c.has_human), 1), else_=0)).label("human_only"),
            func.sum(case((and_(sub.c.has_bot, sub.c.has_human), 1), else_=0)).label("mixed"),
        ).select_from(sub)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        return {
            "total": row.total or 0,
            "bot_only": int(row.bot_only or 0),
            "human_only": int(row.human_only or 0),
            "mixed": int(row.mixed or 0),
        }

    def get_conversation_type_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily conversation classification trend for stacked area chart."""
        from app.models.schemas import Message
        m = Message.__table__
        w = self._tenant_filter(m, tenant_filter)
        if start_date and end_date:
            w = and_(w, m.c.date >= start_date, m.c.date <= end_date)

        sub = (
            select(
                m.c.conversation_id,
                func.min(m.c.date).label("date"),
                func.bool_or(m.c.is_bot).label("has_bot"),
                func.bool_or(m.c.is_human).label("has_human"),
            )
            .where(and_(w, m.c.conversation_id.isnot(None)))
            .group_by(m.c.conversation_id)
            .subquery()
        )

        stmt = (
            select(
                sub.c.date,
                func.sum(case((and_(sub.c.has_bot, ~sub.c.has_human), 1), else_=0)).label("bot_only"),
                func.sum(case((and_(~sub.c.has_bot, sub.c.has_human), 1), else_=0)).label("human_only"),
                func.sum(case((and_(sub.c.has_bot, sub.c.has_human), 1), else_=0)).label("mixed"),
            )
            .select_from(sub)
            .group_by(sub.c.date)
            .order_by(sub.c.date)
        )
        return self._exec(stmt)

    def get_dead_time_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily average dead time from analytics dim_conversation."""
        try:
            sql = text("""
                SELECT date(created_at) AS date,
                       AVG(dead_time_seconds) AS avg_dead_time_seconds
                FROM public_analytics.dim_conversation
                WHERE dead_time_seconds IS NOT NULL
                  AND (:start IS NULL OR date(created_at) >= :start)
                  AND (:end IS NULL OR date(created_at) <= :end)
                GROUP BY date(created_at)
                ORDER BY date(created_at)
            """)
            with engine.connect() as conn:
                return pd.read_sql(sql, conn, params={"start": start_date, "end": end_date})
        except Exception:
            log.warning("Analytics schema unavailable for dead_time_trend")
            return pd.DataFrame(columns=["date", "avg_dead_time_seconds"])

    def get_managed_vs_unmanaged(
        self,
        tenant_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Contact coverage: managed (has conversations) vs unmanaged."""
        try:
            sql = text("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN has_conversations THEN 1 ELSE 0 END) AS managed,
                    SUM(CASE WHEN NOT has_conversations THEN 1 ELSE 0 END) AS unmanaged
                FROM public_analytics.dim_contact
            """)
            with engine.connect() as conn:
                row = conn.execute(sql).first()
            total = row.total or 0
            managed = int(row.managed or 0)
            return {
                "total": total,
                "managed": managed,
                "unmanaged": int(row.unmanaged or 0),
                "managed_pct": round(managed / total * 100, 1) if total > 0 else 0,
            }
        except Exception:
            log.warning("Analytics schema unavailable for managed_vs_unmanaged")
            return {"total": 0, "managed": 0, "unmanaged": 0, "managed_pct": 0}
