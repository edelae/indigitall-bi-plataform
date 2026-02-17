"""
Toques Data Service — Campaigns domain queries.
Migrated from Demo CSV reads → SQLAlchemy Core queries.
"""

import pandas as pd
from sqlalchemy import select, func, and_, literal
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.database import engine
from app.models.schemas import ToquesDaily, Campaign, ToquesHeatmap, ToquesUsuario


class ToquesDataService:
    """Service for querying campaign/touch analytics data."""

    DIAS_SEMANA_ORDER = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

    def _exec(self, stmt) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _daily_filter(self, channels=None, project=None):
        """Build WHERE clauses for toques_daily."""
        t = ToquesDaily.__table__
        clauses = []
        if channels:
            clauses.append(t.c.canal.in_(channels))
        if project and project != "Todos":
            clauses.append(t.c.proyecto_cuenta == project)
        return and_(*clauses) if clauses else True

    def _campaign_filter(self, channels=None, project=None):
        t = Campaign.__table__
        clauses = []
        if channels:
            clauses.append(t.c.canal.in_(channels))
        if project and project != "Todos":
            clauses.append(t.c.proyecto_cuenta == project)
        return and_(*clauses) if clauses else True

    # ==================== KPIs ====================

    def get_kpis(self, channels=None, project=None) -> Dict[str, Any]:
        t = ToquesDaily.__table__
        w = self._daily_filter(channels, project)
        stmt = select(
            func.coalesce(func.sum(t.c.enviados), 0).label("total_enviados"),
            func.coalesce(func.sum(t.c.clicks), 0).label("total_clicks"),
            func.coalesce(func.sum(t.c.chunks), 0).label("total_chunks"),
            func.coalesce(func.sum(t.c.usuarios_unicos), 0).label("usuarios_unicos"),
        ).where(w)

        with engine.connect() as conn:
            row = conn.execute(stmt).first()

        total_env = int(row.total_enviados)
        total_cl = int(row.total_clicks)

        return {
            "total_enviados": total_env,
            "total_clicks": total_cl,
            "total_chunks": int(row.total_chunks),
            "ctr_promedio": round(total_cl / total_env * 100, 2) if total_env > 0 else 0,
            "campanas_activas": self._get_active_campaigns_count(channels, project),
            "usuarios_unicos": int(row.usuarios_unicos),
        }

    def _get_active_campaigns_count(self, channels=None, project=None) -> int:
        t = Campaign.__table__
        today = datetime.now().date()
        w = and_(self._campaign_filter(channels, project), t.c.fecha_fin >= today)
        stmt = select(func.count()).where(w)
        with engine.connect() as conn:
            return conn.execute(stmt).scalar() or 0

    # ==================== Chart Data ====================

    def get_sends_vs_chunks(self, channels=None, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        stmt = (
            select(t.c.date, func.sum(t.c.enviados).label("enviados"), func.sum(t.c.chunks).label("chunks"))
            .where(self._daily_filter(channels, project))
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        return self._exec(stmt)

    def get_sends_clicks_ctr(self, channels=None, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        stmt = (
            select(t.c.date, func.sum(t.c.enviados).label("enviados"), func.sum(t.c.clicks).label("clicks"))
            .where(self._daily_filter(channels, project))
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["enviados"] * 100).round(2).fillna(0)
        return df

    def get_campaigns_by_volume(self, channels=None, project=None, limit=10) -> pd.DataFrame:
        t = Campaign.__table__
        stmt = (
            select(t.c.campana_nombre, t.c.canal, t.c.total_enviados, t.c.ctr)
            .where(self._campaign_filter(channels, project))
            .order_by(t.c.total_enviados.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_campaigns_by_ctr(self, channels=None, project=None, limit=10) -> pd.DataFrame:
        t = Campaign.__table__
        stmt = (
            select(t.c.campana_nombre, t.c.canal, t.c.ctr, t.c.total_enviados)
            .where(and_(self._campaign_filter(channels, project), t.c.total_enviados >= 100))
            .order_by(t.c.ctr.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    def get_heatmap_data(self, channels=None, metric="enviados") -> pd.DataFrame:
        t = ToquesHeatmap.__table__
        w = t.c.canal.in_(channels) if channels else True
        stmt = (
            select(t.c.dia_semana, t.c.hora, func.sum(t.c.enviados).label("enviados"),
                   func.sum(t.c.clicks).label("clicks"), t.c.dia_orden)
            .where(w)
            .group_by(t.c.dia_semana, t.c.hora, t.c.dia_orden)
            .order_by(t.c.dia_orden, t.c.hora)
        )
        df = self._exec(stmt)
        if not df.empty:
            if metric == "ctr":
                df["value"] = (df["clicks"] / df["enviados"] * 100).round(2).fillna(0)
            else:
                df["value"] = df[metric]
        return df[["dia_semana", "hora", "value"]] if not df.empty else pd.DataFrame(columns=["dia_semana", "hora", "value"])

    # ==================== Table Data ====================

    def get_campaign_details(self, channels=None, project=None) -> pd.DataFrame:
        t = Campaign.__table__
        stmt = (
            select(
                t.c.campana_id, t.c.campana_nombre, t.c.canal, t.c.proyecto_cuenta,
                t.c.total_enviados, t.c.total_entregados, t.c.total_clicks, t.c.ctr,
                t.c.fecha_inicio, t.c.fecha_fin,
            )
            .where(self._campaign_filter(channels, project))
            .order_by(t.c.total_enviados.desc())
        )
        return self._exec(stmt)

    def get_users_high_volume(self, threshold=4, channels=None, project=None, limit=100) -> pd.DataFrame:
        t = ToquesUsuario.__table__
        clauses = [t.c.total_toques > threshold]
        if channels:
            clauses.append(t.c.canal.in_(channels))
        if project and project != "Todos":
            clauses.append(t.c.proyecto_cuenta == project)

        stmt = (
            select(t.c.telefono, t.c.canal, t.c.proyecto_cuenta,
                   t.c.total_toques, t.c.total_clicks, t.c.dias_activos)
            .where(and_(*clauses))
            .order_by(t.c.total_toques.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    # ==================== Filter Options ====================

    def get_projects(self) -> List[str]:
        t = ToquesDaily.__table__
        stmt = select(func.distinct(t.c.proyecto_cuenta)).order_by(t.c.proyecto_cuenta)
        df = self._exec(stmt)
        return df.iloc[:, 0].tolist() if not df.empty else []

    def get_channels(self) -> List[str]:
        t = ToquesDaily.__table__
        stmt = select(func.distinct(t.c.canal)).order_by(t.c.canal)
        df = self._exec(stmt)
        return df.iloc[:, 0].tolist() if not df.empty else []

    def get_date_range(self) -> Dict[str, Any]:
        t = ToquesDaily.__table__
        stmt = select(func.min(t.c.date).label("min_date"), func.max(t.c.date).label("max_date"))
        with engine.connect() as conn:
            row = conn.execute(stmt).first()
        return {"min_date": row.min_date, "max_date": row.max_date}

    # ==================== Channel Comparison ====================

    def get_channel_summary(self) -> pd.DataFrame:
        t = ToquesDaily.__table__
        stmt = (
            select(
                t.c.canal,
                func.sum(t.c.enviados).label("enviados"),
                func.sum(t.c.clicks).label("clicks"),
                func.sum(t.c.chunks).label("chunks"),
                func.sum(t.c.usuarios_unicos).label("usuarios_unicos"),
            )
            .group_by(t.c.canal)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["enviados"] * 100).round(2).fillna(0)
        return df

    def get_daily_trend_by_channel(self) -> pd.DataFrame:
        t = ToquesDaily.__table__
        stmt = (
            select(t.c.date, t.c.canal, func.sum(t.c.enviados).label("enviados"),
                   func.sum(t.c.clicks).label("clicks"))
            .group_by(t.c.date, t.c.canal)
            .order_by(t.c.date)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["enviados"] * 100).round(2).fillna(0)
        return df

    # ==================== Email ====================

    def get_email_kpis(self, project=None) -> Dict[str, Any]:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "Email", self._daily_filter(project=project))
        stmt = select(
            func.coalesce(func.sum(t.c.enviados), 0).label("total_enviados"),
            func.coalesce(func.sum(t.c.entregados), 0).label("total_entregados"),
            func.coalesce(func.sum(t.c.abiertos), 0).label("total_abiertos"),
            func.coalesce(func.sum(t.c.clicks), 0).label("total_clicks"),
            func.coalesce(func.sum(t.c.rebotes), 0).label("total_rebotes"),
            func.coalesce(func.sum(t.c.bloqueados), 0).label("total_bloqueados"),
            func.coalesce(func.sum(t.c.spam), 0).label("total_spam"),
            func.coalesce(func.sum(t.c.desuscritos), 0).label("total_desuscritos"),
        ).where(w)

        with engine.connect() as conn:
            r = conn.execute(stmt).first()

        env, ent, ab, cl = int(r.total_enviados), int(r.total_entregados), int(r.total_abiertos), int(r.total_clicks)
        reb, blq, sp, des = int(r.total_rebotes), int(r.total_bloqueados), int(r.total_spam), int(r.total_desuscritos)

        return {
            "total_enviados": env,
            "total_entregados": ent,
            "total_abiertos": ab,
            "total_clicks": cl,
            "open_rate": round(ab / ent * 100, 2) if ent > 0 else 0,
            "ctr": round(cl / ab * 100, 2) if ab > 0 else 0,
            "pct_rebotes": round(reb / env * 100, 2) if env > 0 else 0,
            "pct_bloqueados": round(blq / env * 100, 2) if env > 0 else 0,
            "pct_spam": round(sp / ent * 100, 2) if ent > 0 else 0,
            "pct_desuscritos": round(des / ent * 100, 2) if ent > 0 else 0,
            "campanas_activas": self._get_active_campaigns_count(channels=["Email"], project=project),
        }

    def get_email_engagement_trend(self, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "Email", self._daily_filter(project=project))
        stmt = (
            select(t.c.date,
                   func.sum(t.c.enviados).label("enviados"),
                   func.sum(t.c.entregados).label("entregados"),
                   func.sum(t.c.abiertos).label("abiertos"),
                   func.sum(t.c.clicks).label("clicks"))
            .where(w)
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["open_rate"] = (df["abiertos"] / df["entregados"] * 100).round(2).fillna(0)
            df["ctr"] = (df["clicks"] / df["abiertos"] * 100).round(2).fillna(0)
        return df

    def get_email_error_breakdown(self, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "Email", self._daily_filter(project=project))
        stmt = select(
            func.coalesce(func.sum(t.c.rebotes), 0).label("rebotes"),
            func.coalesce(func.sum(t.c.bloqueados), 0).label("bloqueados"),
            func.coalesce(func.sum(t.c.spam), 0).label("spam"),
            func.coalesce(func.sum(t.c.desuscritos), 0).label("desuscritos"),
        ).where(w)

        with engine.connect() as conn:
            r = conn.execute(stmt).first()

        return pd.DataFrame([
            {"tipo": "Rebotes", "cantidad": int(r.rebotes)},
            {"tipo": "Bloqueados", "cantidad": int(r.bloqueados)},
            {"tipo": "Spam", "cantidad": int(r.spam)},
            {"tipo": "Desuscritos", "cantidad": int(r.desuscritos)},
        ])

    def get_email_campaign_details(self, project=None) -> pd.DataFrame:
        t = Campaign.__table__
        w = and_(t.c.canal == "Email", self._campaign_filter(project=project))
        stmt = (
            select(t.c.campana_id, t.c.campana_nombre, t.c.proyecto_cuenta,
                   t.c.total_enviados, t.c.total_entregados, t.c.total_abiertos,
                   t.c.total_clicks, t.c.open_rate, t.c.ctr,
                   t.c.fecha_inicio, t.c.fecha_fin)
            .where(w)
            .order_by(t.c.total_enviados.desc())
        )
        return self._exec(stmt)

    def get_email_campaigns_by_engagement(self, project=None, limit=10) -> pd.DataFrame:
        t = Campaign.__table__
        w = and_(t.c.canal == "Email", self._campaign_filter(project=project), t.c.total_enviados >= 100)
        stmt = (
            select(t.c.campana_nombre, t.c.open_rate, t.c.ctr, t.c.total_enviados)
            .where(w)
            .order_by(t.c.open_rate.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    # ==================== In-App/Web ====================

    def get_inapp_kpis(self, project=None) -> Dict[str, Any]:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "In App/Web", self._daily_filter(project=project))
        stmt = select(
            func.coalesce(func.sum(t.c.enviados), 0).label("total_impresiones"),
            func.coalesce(func.sum(t.c.clicks), 0).label("total_clicks"),
            func.coalesce(func.sum(t.c.conversiones), 0).label("total_conversiones"),
        ).where(w)

        with engine.connect() as conn:
            r = conn.execute(stmt).first()

        imp, cl, conv = int(r.total_impresiones), int(r.total_clicks), int(r.total_conversiones)
        return {
            "total_impresiones": imp,
            "total_clicks": cl,
            "total_conversiones": conv,
            "ctr": round(cl / imp * 100, 2) if imp > 0 else 0,
            "conversion_rate": round(conv / cl * 100, 2) if cl > 0 else 0,
            "campanas_activas": self._get_active_campaigns_count(channels=["In App/Web"], project=project),
        }

    def get_inapp_engagement_trend(self, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "In App/Web", self._daily_filter(project=project))
        stmt = (
            select(t.c.date,
                   func.sum(t.c.enviados).label("impresiones"),
                   func.sum(t.c.clicks).label("clicks"),
                   func.sum(t.c.conversiones).label("conversiones"))
            .where(w)
            .group_by(t.c.date)
            .order_by(t.c.date)
        )
        df = self._exec(stmt)
        if not df.empty:
            df["ctr"] = (df["clicks"] / df["impresiones"] * 100).round(2).fillna(0)
            df["conversion_rate"] = (df["conversiones"] / df["clicks"] * 100).round(2).fillna(0)
        return df

    def get_inapp_conversion_funnel(self, project=None) -> pd.DataFrame:
        t = ToquesDaily.__table__
        w = and_(t.c.canal == "In App/Web", self._daily_filter(project=project))
        stmt = select(
            func.coalesce(func.sum(t.c.enviados), 0).label("imp"),
            func.coalesce(func.sum(t.c.clicks), 0).label("cl"),
            func.coalesce(func.sum(t.c.conversiones), 0).label("conv"),
        ).where(w)

        with engine.connect() as conn:
            r = conn.execute(stmt).first()

        return pd.DataFrame([
            {"etapa": "Impresiones", "cantidad": int(r.imp)},
            {"etapa": "Clicks", "cantidad": int(r.cl)},
            {"etapa": "Conversiones", "cantidad": int(r.conv)},
        ])

    def get_inapp_campaign_details(self, project=None) -> pd.DataFrame:
        t = Campaign.__table__
        w = and_(t.c.canal == "In App/Web", self._campaign_filter(project=project))
        stmt = (
            select(t.c.campana_id, t.c.campana_nombre, t.c.proyecto_cuenta,
                   t.c.total_enviados, t.c.total_clicks, t.c.total_conversiones,
                   t.c.ctr, t.c.conversion_rate, t.c.fecha_inicio, t.c.fecha_fin)
            .where(w)
            .order_by(t.c.total_enviados.desc())
        )
        df = self._exec(stmt)
        if not df.empty and "total_enviados" in df.columns:
            df = df.rename(columns={"total_enviados": "total_impresiones"})
        return df

    def get_inapp_campaigns_by_conversion(self, project=None, limit=10) -> pd.DataFrame:
        t = Campaign.__table__
        w = and_(t.c.canal == "In App/Web", self._campaign_filter(project=project), t.c.total_enviados >= 100)
        stmt = (
            select(t.c.campana_nombre, t.c.conversion_rate, t.c.ctr, t.c.total_enviados)
            .where(w)
            .order_by(t.c.conversion_rate.desc())
            .limit(limit)
        )
        return self._exec(stmt)

    # ==================== Export ====================

    def get_export_data(self, data_type="campaigns", channels=None, project=None) -> pd.DataFrame:
        if data_type == "campaigns":
            return self.get_campaign_details(channels, project)
        elif data_type == "daily":
            t = ToquesDaily.__table__
            return self._exec(select(t).where(self._daily_filter(channels, project)))
        elif data_type == "users":
            return self.get_users_high_volume(threshold=0, channels=channels, project=project, limit=10000)
        elif data_type == "email":
            return self.get_email_campaign_details(project)
        elif data_type == "inapp":
            return self.get_inapp_campaign_details(project)
        return pd.DataFrame()
