"""General Dashboard Service — Cross-channel overview queries."""

import logging

import pandas as pd
from datetime import date as date_type
from sqlalchemy import select, func, and_, case
from typing import Optional, Dict, Any

from app.models.database import engine
from app.models.schemas import Message, ChatConversation, Contact, SmsEnvio
from app.services.analytics_service import AnalyticsService

log = logging.getLogger(__name__)


class GeneralDashboardService:
    """Service for composing cross-channel KPIs and comparisons.

    Delegates to AnalyticsService when the star schema is available,
    falls back to direct table queries otherwise.
    """

    def __init__(self):
        self._analytics = AnalyticsService()

    def _exec(self, stmt) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _tenant_filter(self, table, tenant_id: Optional[str]):
        if tenant_id:
            return table.c.tenant_id == tenant_id
        return True

    def get_overview_kpis(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """Cross-channel KPIs from star schema or fallback."""
        if self._analytics.is_available() and start_date and end_date:
            return self._analytics.get_overview_kpis(
                tenant_id=tenant_filter,
                start_date=start_date,
                end_date=end_date,
            )
        return self._get_overview_kpis_fallback(tenant_filter, start_date, end_date)

    def get_channel_summary_table(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """One row per channel with key metrics."""
        if self._analytics.is_available() and start_date and end_date:
            return self._analytics.get_channel_comparison(
                tenant_id=tenant_filter,
                start_date=start_date,
                end_date=end_date,
            )
        return self._get_channel_summary_fallback(tenant_filter, start_date, end_date)

    def get_combined_daily_trend(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily event counts by channel."""
        if self._analytics.is_available() and start_date and end_date:
            return self._analytics.get_daily_trend_by_channel(
                tenant_id=tenant_filter,
                start_date=start_date,
                end_date=end_date,
            )
        return self._get_combined_daily_trend_fallback(
            tenant_filter, start_date, end_date
        )

    def get_delivery_funnel(
        self,
        tenant_filter: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Delivery funnel: Enviado -> Entregado -> Leido -> Click."""
        if self._analytics.is_available() and start_date and end_date:
            return self._analytics.get_delivery_funnel(
                tenant_id=tenant_filter,
                start_date=start_date,
                end_date=end_date,
            )
        return pd.DataFrame()

    # ==================== Fallback queries ====================

    def _get_overview_kpis_fallback(
        self,
        tenant_filter: Optional[str],
        start_date: Optional[date_type],
        end_date: Optional[date_type],
    ) -> Dict[str, Any]:
        """Original 4-query KPIs when star schema is not available."""
        with engine.connect() as conn:
            mt = Message.__table__
            mw = self._tenant_filter(mt, tenant_filter)
            if start_date and end_date:
                mw = and_(mw, mt.c.date >= start_date, mt.c.date <= end_date)
            msg_row = conn.execute(
                select(
                    func.count().label("wa_messages"),
                    func.sum(case(
                        (mt.c.status.in_(["channel_delivered", "channel_read"]), 1),
                        else_=0,
                    )).label("wa_delivered"),
                ).where(mw)
            ).first()

            ct = ChatConversation.__table__
            cw = self._tenant_filter(ct, tenant_filter)
            if start_date and end_date:
                cw = and_(
                    cw,
                    func.date(ct.c.closed_at) >= start_date,
                    func.date(ct.c.closed_at) <= end_date,
                )
            cc_row = conn.execute(
                select(func.count().label("cc_conversations")).where(cw)
            ).first()

            st = SmsEnvio.__table__
            sw = True
            if start_date and end_date:
                sw = and_(
                    func.date(st.c.sent_at) >= start_date,
                    func.date(st.c.sent_at) <= end_date,
                )
            sms_row = conn.execute(
                select(
                    func.count().label("sms_total"),
                    func.sum(case(
                        (st.c.status == "DELIVRD", 1), else_=0
                    )).label("sms_delivered"),
                ).where(sw)
            ).first()

            cont_t = Contact.__table__
            cont_w = self._tenant_filter(cont_t, tenant_filter)
            total_contacts = conn.execute(
                select(func.count()).select_from(cont_t).where(cont_w)
            ).scalar() or 0

        wa_msgs = msg_row.wa_messages or 0
        wa_del = msg_row.wa_delivered or 0
        sms_total = sms_row.sms_total or 0
        sms_del = sms_row.sms_delivered or 0
        sent = wa_msgs + sms_total
        delivered = wa_del + sms_del

        return {
            "total_events": sent + (cc_row.cc_conversations or 0),
            "total_sent": sent,
            "total_delivered": delivered,
            "total_read_opened": 0,
            "total_clicked": 0,
            "total_errors": 0,
            "delivery_rate": round(delivered / sent * 100, 1) if sent > 0 else 0,
            "read_rate": 0,
            "ctr": 0,
        }

    def _get_channel_summary_fallback(
        self,
        tenant_filter: Optional[str],
        start_date: Optional[date_type],
        end_date: Optional[date_type],
    ) -> pd.DataFrame:
        """Original 3-row channel table when star schema is not available."""
        kpis = self._get_overview_kpis_fallback(tenant_filter, start_date, end_date)
        return pd.DataFrame([
            {
                "channel_name": "WhatsApp",
                "enviados": kpis["total_sent"],
                "entregados": kpis["total_delivered"],
                "tasa_entrega": kpis["delivery_rate"],
                "leidos": 0,
                "tasa_lectura": 0,
                "clicks": 0,
                "ctr": 0,
                "errores": 0,
            },
        ])

    def _get_combined_daily_trend_fallback(
        self,
        tenant_filter: Optional[str],
        start_date: Optional[date_type],
        end_date: Optional[date_type],
    ) -> pd.DataFrame:
        """Original 3-query merge when star schema is not available."""
        mt = Message.__table__
        mw = self._tenant_filter(mt, tenant_filter)
        if start_date and end_date:
            mw = and_(mw, mt.c.date >= start_date, mt.c.date <= end_date)
        wa_df = self._exec(
            select(mt.c.date, func.count().label("WhatsApp"))
            .where(mw)
            .group_by(mt.c.date)
        )

        ct = ChatConversation.__table__
        cw = self._tenant_filter(ct, tenant_filter)
        if start_date and end_date:
            cw = and_(
                cw,
                func.date(ct.c.closed_at) >= start_date,
                func.date(ct.c.closed_at) <= end_date,
            )
        cc_date = func.date(ct.c.closed_at).label("date")
        cc_df = self._exec(
            select(cc_date, func.count().label("Contact Center"))
            .where(cw)
            .group_by(cc_date)
        )

        st = SmsEnvio.__table__
        sw = True
        if start_date and end_date:
            sw = and_(
                func.date(st.c.sent_at) >= start_date,
                func.date(st.c.sent_at) <= end_date,
            )
        sms_date = func.date(st.c.sent_at).label("date")
        sms_df = self._exec(
            select(sms_date, func.count().label("SMS"))
            .where(sw)
            .group_by(sms_date)
        )

        if wa_df.empty and cc_df.empty and sms_df.empty:
            return pd.DataFrame()

        merged = wa_df.set_index("date") if not wa_df.empty else pd.DataFrame()
        if not cc_df.empty:
            cc_df = cc_df.set_index("date")
            merged = merged.join(cc_df, how="outer") if not merged.empty else cc_df
        if not sms_df.empty:
            sms_df = sms_df.set_index("date")
            merged = merged.join(sms_df, how="outer") if not merged.empty else sms_df

        merged = merged.fillna(0).reset_index()
        merged = merged.rename(columns={"index": "date"})
        return merged.sort_values("date")
