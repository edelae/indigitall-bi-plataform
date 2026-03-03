"""Analytics Service — Queries the public_analytics star schema."""

import logging

import pandas as pd
from datetime import date as date_type
from sqlalchemy import text
from typing import Optional, Dict, Any

from app.models.database import engine

log = logging.getLogger(__name__)


class AnalyticsService:
    """Service for querying the analytics star schema (public_analytics.*)."""

    def __init__(self):
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "SELECT 1 FROM public_analytics.fact_message_events LIMIT 1"
                ))
            return True
        except Exception:
            log.info("Analytics star schema not available, using fallback")
            return False

    def is_available(self) -> bool:
        return self._available

    def get_overview_kpis(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """Cross-channel KPIs from the unified fact table."""
        sql = text("""
            SELECT
                COALESCE(SUM(f.event_count), 0) AS total_events,
                COALESCE(SUM(CASE WHEN et.event_code = 'sent'
                    THEN f.event_count ELSE 0 END), 0) AS total_sent,
                COALESCE(SUM(CASE WHEN et.event_code = 'delivered'
                    THEN f.event_count ELSE 0 END), 0) AS total_delivered,
                COALESCE(SUM(CASE WHEN et.event_code IN ('read', 'opened')
                    THEN f.event_count ELSE 0 END), 0) AS total_read_opened,
                COALESCE(SUM(CASE WHEN et.event_code = 'clicked'
                    THEN f.event_count ELSE 0 END), 0) AS total_clicked,
                COALESCE(SUM(CASE WHEN et.event_category = 'error'
                    THEN f.event_count ELSE 0 END), 0) AS total_errors
            FROM public_analytics.fact_message_events f
            JOIN public_analytics.dim_event_type et
                ON et.event_type_key = f.event_type_key
            JOIN public_analytics.dim_date d
                ON d.date_key = f.date_key
            WHERE d.full_date BETWEEN :start_date AND :end_date
        """)
        with engine.connect() as conn:
            row = conn.execute(
                sql, {"start_date": start_date, "end_date": end_date}
            ).first()

        sent = row.total_sent or 0
        delivered = row.total_delivered or 0
        read_opened = row.total_read_opened or 0
        clicked = row.total_clicked or 0

        return {
            "total_events": row.total_events or 0,
            "total_sent": sent,
            "total_delivered": delivered,
            "total_read_opened": read_opened,
            "total_clicked": clicked,
            "total_errors": row.total_errors or 0,
            "delivery_rate": round(delivered / sent * 100, 1) if sent > 0 else 0,
            "read_rate": round(read_opened / delivered * 100, 1) if delivered > 0 else 0,
            "ctr": round(clicked / delivered * 100, 2) if delivered > 0 else 0,
        }

    def get_delivery_funnel(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Delivery funnel stages: Enviado -> Entregado -> Leido/Abierto -> Click."""
        sql = text("""
            SELECT
                COALESCE(SUM(CASE WHEN et.event_code = 'sent'
                    THEN f.event_count ELSE 0 END), 0) AS enviados,
                COALESCE(SUM(CASE WHEN et.event_code = 'delivered'
                    THEN f.event_count ELSE 0 END), 0) AS entregados,
                COALESCE(SUM(CASE WHEN et.event_code IN ('read', 'opened')
                    THEN f.event_count ELSE 0 END), 0) AS leidos,
                COALESCE(SUM(CASE WHEN et.event_code = 'clicked'
                    THEN f.event_count ELSE 0 END), 0) AS clicks
            FROM public_analytics.fact_message_events f
            JOIN public_analytics.dim_event_type et
                ON et.event_type_key = f.event_type_key
            JOIN public_analytics.dim_date d
                ON d.date_key = f.date_key
            WHERE d.full_date BETWEEN :start_date AND :end_date
        """)
        with engine.connect() as conn:
            row = conn.execute(
                sql, {"start_date": start_date, "end_date": end_date}
            ).first()

        return pd.DataFrame([
            {"etapa": "Enviados", "cantidad": row.enviados or 0},
            {"etapa": "Entregados", "cantidad": row.entregados or 0},
            {"etapa": "Leidos/Abiertos", "cantidad": row.leidos or 0},
            {"etapa": "Clicks", "cantidad": row.clicks or 0},
        ])

    def get_channel_comparison(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """One row per active channel with delivery and engagement metrics."""
        sql = text("""
            SELECT
                ch.channel_name,
                COALESCE(SUM(CASE WHEN et.event_code = 'sent'
                    THEN f.event_count ELSE 0 END), 0) AS enviados,
                COALESCE(SUM(CASE WHEN et.event_code = 'delivered'
                    THEN f.event_count ELSE 0 END), 0) AS entregados,
                COALESCE(SUM(CASE WHEN et.event_code IN ('read', 'opened')
                    THEN f.event_count ELSE 0 END), 0) AS leidos,
                COALESCE(SUM(CASE WHEN et.event_code = 'clicked'
                    THEN f.event_count ELSE 0 END), 0) AS clicks,
                COALESCE(SUM(CASE WHEN et.event_category = 'error'
                    THEN f.event_count ELSE 0 END), 0) AS errores
            FROM public_analytics.fact_message_events f
            JOIN public_analytics.dim_channel ch
                ON ch.channel_key = f.channel_key
            JOIN public_analytics.dim_event_type et
                ON et.event_type_key = f.event_type_key
            JOIN public_analytics.dim_date d
                ON d.date_key = f.date_key
            WHERE d.full_date BETWEEN :start_date AND :end_date
            GROUP BY ch.channel_name, ch.display_order
            HAVING SUM(f.event_count) > 0
            ORDER BY ch.display_order
        """)
        with engine.connect() as conn:
            df = pd.read_sql(
                sql, conn, params={"start_date": start_date, "end_date": end_date}
            )

        if df.empty:
            return df

        df["tasa_entrega"] = df.apply(
            lambda r: round(r["entregados"] / r["enviados"] * 100, 1)
            if r["enviados"] > 0 else 0, axis=1
        )
        df["tasa_lectura"] = df.apply(
            lambda r: round(r["leidos"] / r["entregados"] * 100, 1)
            if r["entregados"] > 0 else 0, axis=1
        )
        df["ctr"] = df.apply(
            lambda r: round(r["clicks"] / r["entregados"] * 100, 2)
            if r["entregados"] > 0 else 0, axis=1
        )

        return df[["channel_name", "enviados", "entregados", "tasa_entrega",
                    "leidos", "tasa_lectura", "clicks", "ctr", "errores"]]

    def get_daily_trend_by_channel(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """Daily event counts pivoted by channel_name."""
        sql = text("""
            SELECT
                d.full_date AS date,
                ch.channel_name,
                SUM(f.event_count) AS events
            FROM public_analytics.fact_message_events f
            JOIN public_analytics.dim_channel ch
                ON ch.channel_key = f.channel_key
            JOIN public_analytics.dim_event_type et
                ON et.event_type_key = f.event_type_key
            JOIN public_analytics.dim_date d
                ON d.date_key = f.date_key
            WHERE d.full_date BETWEEN :start_date AND :end_date
              AND et.event_code = 'sent'
            GROUP BY d.full_date, ch.channel_name
            ORDER BY d.full_date
        """)
        with engine.connect() as conn:
            df = pd.read_sql(
                sql, conn, params={"start_date": start_date, "end_date": end_date}
            )

        if df.empty:
            return df

        pivot = df.pivot(index="date", columns="channel_name", values="events")
        pivot = pivot.fillna(0).reset_index()
        pivot = pivot.sort_values("date")
        return pivot
