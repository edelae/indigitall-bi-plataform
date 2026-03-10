"""SMS Data Service — Queries for sms_envios + sms_daily_stats.

sms_envios columns: id, tenant_id, sending_id, application_id, campaign_id,
  total_chunks, sending_type, is_flash, sent_at
  NOTE: total_chunks is NULL for all rows (API doesn't return per-send chunks).

sms_daily_stats columns: id, tenant_id, application_id, date,
  total_sent, total_delivered, total_rejected, total_chunks,
  total_clicks, unique_contacts, total_cost
  NOTE: This table has actual chunk/delivery/click data from /v2/sms/stats/application.
"""

import pandas as pd
from datetime import date as date_type
from sqlalchemy import select, func, and_, text
from typing import Optional, Dict, Any, Tuple

from app.models.database import engine
from app.models.schemas import SmsEnvio, SmsDailyStat


class SmsDataService:
    """Service for querying SMS sending data from sms_envios."""

    def _exec(self, stmt) -> pd.DataFrame:
        try:
            with engine.connect() as conn:
                return pd.read_sql(stmt, conn)
        except Exception:
            return pd.DataFrame()

    def _base_where(self, t, start_date, end_date):
        w = True
        if start_date and end_date:
            w = and_(func.date(t.c.sent_at) >= start_date, func.date(t.c.sent_at) <= end_date)
        return w

    def _daily_where(self, d, start_date, end_date):
        w = True
        if start_date and end_date:
            w = and_(d.c.date >= start_date, d.c.date <= end_date)
        return w

    def get_sms_kpis(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """KPIs combining sms_envios (campaigns) + sms_daily_stats (chunks, delivery, clicks)."""
        empty = {
            "total_enviados": 0, "total_chunks": 0, "total_delivered": 0,
            "total_clicks": 0, "campanas": 0, "tipos_envio": 0,
        }
        try:
            # Campaigns and sending types from sms_envios
            t = SmsEnvio.__table__
            w = self._base_where(t, start_date, end_date)
            stmt1 = select(
                func.count().label("total_enviados"),
                func.count(func.distinct(t.c.campaign_id)).label("campanas"),
                func.count(func.distinct(t.c.sending_type)).label("tipos_envio"),
            ).where(w)

            # Chunks, delivered, clicks from sms_daily_stats
            d = SmsDailyStat.__table__
            dw = self._daily_where(d, start_date, end_date)
            stmt2 = select(
                func.coalesce(func.sum(d.c.total_chunks), 0).label("total_chunks"),
                func.coalesce(func.sum(d.c.total_delivered), 0).label("total_delivered"),
                func.coalesce(func.sum(d.c.total_clicks), 0).label("total_clicks"),
            ).where(dw)

            with engine.connect() as conn:
                r1 = conn.execute(stmt1).first()
                r2 = conn.execute(stmt2).first()
            return {
                "total_enviados": r1.total_enviados or 0,
                "total_chunks": r2.total_chunks or 0,
                "total_delivered": r2.total_delivered or 0,
                "total_clicks": r2.total_clicks or 0,
                "campanas": r1.campanas or 0,
                "tipos_envio": r1.tipos_envio or 0,
            }
        except Exception:
            return empty

    def get_sends_vs_chunks_trend(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily sends vs chunks from sms_daily_stats (has real chunk data)."""
        d = SmsDailyStat.__table__
        dw = self._daily_where(d, start_date, end_date)
        stmt = (
            select(
                d.c.date.label("date"),
                func.coalesce(func.sum(d.c.total_sent), 0).label("enviados"),
                func.coalesce(func.sum(d.c.total_chunks), 0).label("chunks"),
            )
            .where(dw)
            .group_by(d.c.date)
            .order_by(d.c.date)
        )
        return self._exec(stmt)

    def get_sends_clicks_ctr_trend(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily sends, clicks and CTR from sms_daily_stats."""
        d = SmsDailyStat.__table__
        dw = self._daily_where(d, start_date, end_date)
        stmt = (
            select(
                d.c.date.label("date"),
                func.coalesce(func.sum(d.c.total_sent), 0).label("enviados"),
                func.coalesce(func.sum(d.c.total_clicks), 0).label("clicks"),
            )
            .where(dw)
            .group_by(d.c.date)
            .order_by(d.c.date)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["enviados"].replace(0, 1) * 100).round(2)
        return df

    def get_campaign_ranking(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top campaigns by volume (campaign_id only, name not available)."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        stmt = (
            select(
                t.c.campaign_id.label("campana_nombre"),
                func.count().label("total_enviados"),
                func.coalesce(func.sum(t.c.total_chunks), 0).label("chunks"),
            )
            .where(and_(w, t.c.campaign_id.isnot(None)))
            .group_by(t.c.campaign_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["campana_nombre"] = "Campana #" + df["campana_nombre"].astype(str)
        return df

    def get_campaign_ranking_by_ctr(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top campaigns by volume (CTR not available, sorted by chunks/send)."""
        t = SmsEnvio.__table__
        w = self._base_where(t, start_date, end_date)
        stmt = (
            select(
                t.c.campaign_id.label("campana_nombre"),
                func.count().label("total_enviados"),
                func.coalesce(func.sum(t.c.total_chunks), 0).label("chunks"),
            )
            .where(and_(w, t.c.campaign_id.isnot(None)))
            .group_by(t.c.campaign_id)
            .having(func.count() > 100)
            .order_by(
                (func.coalesce(func.sum(t.c.total_chunks), 0) * 1.0 / func.count()).desc()
            )
            .limit(limit)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["campana_nombre"] = "Campana #" + df["campana_nombre"].astype(str)
            df["chunks_per_send"] = (df["chunks"] / df["total_enviados"]).round(2)
        return df

    def get_heatmap_data(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Hour x Day-of-week heatmap."""
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
            df["dia_semana"] = df["day_name"].str.strip().map(lambda d: day_map.get(d, d))
            df = df[["dia_semana", "hora", "value"]]
        return df

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

    def get_detail_page(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Tuple[pd.DataFrame, int]:
        """Paginated SMS detail table with total count."""
        try:
            t = SmsEnvio.__table__
            w = self._base_where(t, start_date, end_date)
            with engine.connect() as conn:
                total = conn.execute(
                    select(func.count()).select_from(t).where(w)
                ).scalar() or 0
            stmt = (
                select(
                    func.date(t.c.sent_at).label("fecha"),
                    t.c.campaign_id, t.c.sending_type,
                    t.c.total_chunks, t.c.is_flash,
                )
                .where(w)
                .order_by(t.c.sent_at.desc())
                .offset(page * page_size)
                .limit(page_size)
            )
            return self._exec(stmt), total
        except Exception:
            return pd.DataFrame(), 0

    def get_drill_data(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        granularity: str = "month",
    ) -> pd.DataFrame:
        """Aggregated SMS counts for drill-down (month/week/day) from sms_daily_stats."""
        d = SmsDailyStat.__table__
        dw = self._daily_where(d, start_date, end_date)

        if granularity == "month":
            period = func.to_char(d.c.date, "YYYY-MM").label("period")
        elif granularity == "week":
            period = func.to_char(d.c.date, "IYYY-\"W\"IW").label("period")
        else:
            period = d.c.date.label("period")

        stmt = (
            select(
                period,
                func.coalesce(func.sum(d.c.total_sent), 0).label("total"),
                func.coalesce(func.sum(d.c.total_chunks), 0).label("chunks"),
            )
            .where(dw)
            .group_by(period)
            .order_by(period)
        )
        return self._exec(stmt)
