"""SMS Data Service — Queries for sms_envios (293K records)."""

import pandas as pd
from datetime import date as date_type
from sqlalchemy import select, func, and_, case
from typing import Optional, Dict, Any, Tuple

from app.models.database import engine
from app.models.schemas import SmsEnvio


class SmsDataService:
    """Service for querying detailed SMS sending data from sms_envios."""

    # SMPP standard status codes from the actual data
    DELIVERED_STATUS = "DELIVRD"

    def _exec(self, stmt) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _base_where(self, t, start_date, end_date):
        w = True
        if start_date and end_date:
            w = and_(func.date(t.c.sent_at) >= start_date, func.date(t.c.sent_at) <= end_date)
        return w

    def _delivered_case(self, t):
        return case((t.c.status == self.DELIVERED_STATUS, 1), else_=0)

    def get_sms_kpis(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """KPIs: enviados, clicks, chunks, CTR, campanas, delivery rate."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)

        stmt = select(
            func.count().label("total_enviados"),
            func.coalesce(func.sum(t.c.clicks), 0).label("total_clicks"),
            func.coalesce(func.sum(t.c.total_chunks), 0).label("total_chunks"),
            func.count(func.distinct(t.c.campaign_id)).label("campanas"),
            func.sum(self._delivered_case(t)).label("delivered"),
            func.count(func.distinct(t.c.phone)).label("unique_phones"),
        ).where(w)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        total = row.total_enviados or 0
        clicks = row.total_clicks or 0
        delivered = row.delivered or 0
        return {
            "total_enviados": total,
            "total_clicks": clicks,
            "total_chunks": row.total_chunks or 0,
            "ctr": round(clicks / total * 100, 2) if total > 0 else 0,
            "campanas": row.campanas or 0,
            "delivered": delivered,
            "delivery_rate": round(delivered / total * 100, 2) if total > 0 else 0,
            "unique_phones": row.unique_phones or 0,
        }

    def get_sends_vs_chunks_trend(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily sends vs chunks from sms_envios."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        date_col = func.date(t.c.sent_at).label("date")
        stmt = (
            select(
                date_col,
                func.count().label("enviados"),
                func.coalesce(func.sum(t.c.total_chunks), 0).label("chunks"),
            )
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        return self._exec(stmt)

    def get_sends_clicks_ctr_trend(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily sends, clicks, and CTR from sms_envios."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        date_col = func.date(t.c.sent_at).label("date")
        stmt = (
            select(
                date_col,
                func.count().label("enviados"),
                func.coalesce(func.sum(t.c.clicks), 0).label("clicks"),
            )
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["enviados"] * 100).round(2).fillna(0)
        return df

    def get_campaign_ranking(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top campaigns by volume from sms_envios."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        stmt = (
            select(
                t.c.campaign_name.label("campana_nombre"),
                func.count().label("total_enviados"),
                func.coalesce(func.sum(t.c.clicks), 0).label("clicks"),
            )
            .where(and_(w, t.c.campaign_name.isnot(None)))
            .group_by(t.c.campaign_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["total_enviados"] * 100).round(2).fillna(0)
        return df

    def get_campaign_ranking_by_ctr(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top campaigns by CTR (minimum 100 sends)."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        stmt = (
            select(
                t.c.campaign_name.label("campana_nombre"),
                func.count().label("total_enviados"),
                func.coalesce(func.sum(t.c.clicks), 0).label("clicks"),
            )
            .where(and_(w, t.c.campaign_name.isnot(None)))
            .group_by(t.c.campaign_name)
            .having(func.count() > 100)
            .order_by((func.coalesce(func.sum(t.c.clicks), 0) * 100.0 / func.count()).desc())
            .limit(limit)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["total_enviados"] * 100).round(2).fillna(0)
        return df

    def get_heatmap_data(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Hour x Day-of-week heatmap from sms_envios."""
        t = SmsEnvio.__table__
        w = and_(self._base_where(t, start_date, end_date), t.c.sent_at.isnot(None))
        dow = func.to_char(t.c.sent_at, "Day").label("day_name")
        hour = func.extract("hour", t.c.sent_at).label("hora")
        dow_num = func.extract("isodow", t.c.sent_at).label("dow_num")
        stmt = (
            select(dow, hour, func.count().label("value"), dow_num)
            .where(w)
            .group_by(dow, hour, dow_num)
            .order_by(dow_num, hour)
        )
        df = self._exec(stmt)
        if not df.empty:
            day_map = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
                "Thursday": "Jueves", "Friday": "Viernes",
                "Saturday": "Sabado", "Sunday": "Domingo",
            }
            df["dia_semana"] = df["day_name"].str.strip().map(
                lambda d: day_map.get(d, d)
            )
            df = df[["dia_semana", "hora", "value"]]
        return df

    def get_delivery_rate_trend(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily delivery rate trend."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        date_col = func.date(t.c.sent_at).label("date")
        stmt = (
            select(
                date_col,
                func.count().label("total"),
                func.sum(self._delivered_case(t)).label("delivered"),
            )
            .where(w)
            .group_by(date_col)
            .order_by(date_col)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["rate"] = (df["delivered"] / df["total"] * 100).round(2).fillna(0)
        return df

    def get_status_breakdown(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """SMS counts by status (DELIVRD, REJECTD, UNDELIV, etc.)."""
        t = SmsEnvio.__table__
        w = and_(self._base_where(t, start_date, end_date), t.c.status.isnot(None), t.c.status != "")
        stmt = (
            select(t.c.status, func.count().label("count"))
            .where(w)
            .group_by(t.c.status)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)

    def get_error_breakdown(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """SMS error counts by error description."""
        t = SmsEnvio.__table__
        w = and_(
            self._base_where(t, start_date, end_date),
            t.c.error_description.isnot(None),
            t.c.error_description != "",
        )
        stmt = (
            select(t.c.error_description, func.count().label("count"))
            .where(w)
            .group_by(t.c.error_description)
            .order_by(func.count().desc())
            .limit(10)
        )
        return self._exec(stmt)

    def get_sending_type_breakdown(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """SMS counts by sending type."""
        t = SmsEnvio.__table__
        w = and_(self._base_where(t, start_date, end_date), t.c.sending_type.isnot(None))
        stmt = (
            select(t.c.sending_type, func.count().label("count"))
            .where(w)
            .group_by(t.c.sending_type)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)

    def get_network_breakdown(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """SMS counts and delivery rate by network."""
        t = SmsEnvio.__table__
        w = and_(
            self._base_where(t, start_date, end_date),
            t.c.network_name.isnot(None),
            t.c.network_name != "",
        )
        stmt = (
            select(
                t.c.network_name,
                func.count().label("count"),
                func.sum(self._delivered_case(t)).label("delivered"),
            )
            .where(w)
            .group_by(t.c.network_name)
            .order_by(func.count().desc())
            .limit(10)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["delivery_rate"] = (df["delivered"] / df["count"] * 100).round(2).fillna(0)
        return df

    def get_detail_page(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Tuple[pd.DataFrame, int]:
        """Paginated SMS detail table with total count."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)

        with engine.connect() as conn:
            total = conn.execute(select(func.count()).select_from(t).where(w)).scalar() or 0

        stmt = (
            select(
                func.date(t.c.sent_at).label("fecha"),
                t.c.campaign_name, t.c.phone, t.c.status,
                t.c.network_name, t.c.total_chunks, t.c.clicks,
                t.c.error_description,
            )
            .where(w)
            .order_by(t.c.sent_at.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        return self._exec(stmt), total

    def get_drill_data(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        granularity: str = "month",
    ) -> pd.DataFrame:
        """Aggregated SMS counts for drill-down (month/week/day)."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)

        if granularity == "month":
            period = func.to_char(t.c.sent_at, "YYYY-MM").label("period")
        elif granularity == "week":
            period = func.to_char(t.c.sent_at, "IYYY-\"W\"IW").label("period")
        else:
            period = func.date(t.c.sent_at).label("period")

        stmt = (
            select(
                period,
                func.count().label("total"),
                func.sum(self._delivered_case(t)).label("delivered"),
                func.coalesce(func.sum(t.c.clicks), 0).label("clicks"),
            )
            .where(w)
            .group_by(period)
            .order_by(period)
        )
        return self._exec(stmt)
