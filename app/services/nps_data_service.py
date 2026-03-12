"""NPS Data Service — queries for WhatsApp NPS & Bot analytics dashboard."""

import pandas as pd
from datetime import date as date_type
from typing import Optional, Dict, Any

from sqlalchemy import select, func, case, text, and_

from app.models.database import engine
from app.models.schemas import NpsSurvey, Message


class NpsDataService:
    """Service for NPS survey analytics and bot fallback queries."""

    def _exec(self, stmt) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def _tenant_filter(self, table, tenant_id: Optional[str]):
        if tenant_id:
            return table.c.tenant_id == tenant_id
        return True

    def _date_filter(self, table, start: Optional[date_type], end: Optional[date_type]):
        clauses = []
        if start:
            clauses.append(table.c.date >= start)
        if end:
            clauses.append(table.c.date <= end)
        return clauses

    # ─── NPS KPIs ────────────────────────────────────────────────

    def get_nps_kpis(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        t = NpsSurvey.__table__
        filters = [self._tenant_filter(t, tenant)] + self._date_filter(t, start, end)

        with engine.connect() as conn:
            row = conn.execute(
                select(
                    func.count().label("total_surveys"),
                    func.avg(t.c.score_atencion).label("avg_score_atencion"),
                    func.avg(t.c.score_asesor).label("avg_score_asesor"),
                    func.sum(case((t.c.nps_categoria == "Promotor", 1), else_=0)).label("promotores"),
                    func.sum(case((t.c.nps_categoria == "Pasivo", 1), else_=0)).label("pasivos"),
                    func.sum(case((t.c.nps_categoria == "Detractor", 1), else_=0)).label("detractores"),
                    func.avg(t.c.rapida).label("pct_rapida"),
                    func.avg(t.c.resuelto).label("pct_resuelto"),
                    func.avg(t.c.volveria).label("pct_volveria"),
                    func.count(func.distinct(t.c.entity)).label("entidades"),
                ).where(and_(*filters))
            ).first()

        total = row.total_surveys or 0
        prom = row.promotores or 0
        det = row.detractores or 0
        nps_score = round((prom - det) / total * 100, 1) if total > 0 else 0

        return {
            "total_surveys": total,
            "nps_score": nps_score,
            "avg_score_atencion": round(float(row.avg_score_atencion or 0), 2),
            "avg_score_asesor": round(float(row.avg_score_asesor or 0), 2),
            "promotores": prom,
            "pasivos": row.pasivos or 0,
            "detractores": det,
            "pct_promotores": round(prom / total * 100, 1) if total > 0 else 0,
            "pct_detractores": round(det / total * 100, 1) if total > 0 else 0,
            "pct_rapida": round(float(row.pct_rapida or 0) * 100, 1),
            "pct_resuelto": round(float(row.pct_resuelto or 0) * 100, 1),
            "pct_volveria": round(float(row.pct_volveria or 0) * 100, 1),
            "entidades": row.entidades or 0,
        }

    # ─── NPS vs Canal by period ──────────────────────────────────

    def get_nps_by_canal(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        period: str = "month",
    ) -> pd.DataFrame:
        """NPS metrics grouped by period and canal_tipo.

        Returns columns: periodo, canal_tipo, encuestas, promotores, detractores, nps_score
        """
        if period == "month":
            period_expr = "month_label"
        elif period == "week":
            period_expr = "TO_CHAR(date, 'IYYY-IW')"
        else:
            period_expr = "date::text"

        tenant_clause = f"AND tenant_id = '{tenant}'" if tenant else ""
        date_clauses = ""
        if start:
            date_clauses += f" AND date >= '{start}'"
        if end:
            date_clauses += f" AND date <= '{end}'"

        query = text(f"""
            SELECT
                {period_expr} AS periodo,
                canal_tipo,
                COUNT(*) AS encuestas,
                SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END) AS promotores,
                SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END) AS detractores,
                ROUND(
                    (SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END)
                     - SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END))::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1
                ) AS nps_score
            FROM nps_surveys
            WHERE 1=1 {tenant_clause} {date_clauses}
            GROUP BY {period_expr}, canal_tipo
            ORDER BY {period_expr}, canal_tipo
        """)
        return self._exec(query)

    def get_nps_trend_pivoted(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        period: str = "month",
    ) -> pd.DataFrame:
        """NPS trend pivoted: one row per period with columns for each canal_tipo.

        Returns: periodo, bot_count, agente_count, mixta_count,
                 bot_nps, agente_nps, mixta_nps, total_nps
        """
        raw = self.get_nps_by_canal(tenant, start, end, period)
        if raw.empty:
            return pd.DataFrame()

        periodos = sorted(raw["periodo"].unique())
        result = []

        for p in periodos:
            sub = raw[raw["periodo"] == p]
            row = {"periodo": p}

            total_enc = 0
            total_prom = 0
            total_det = 0

            for canal in ["Bot", "Agente", "Mixta"]:
                c_rows = sub[sub["canal_tipo"] == canal]
                if not c_rows.empty:
                    r = c_rows.iloc[0]
                    row[f"{canal.lower()}_count"] = int(r["encuestas"])
                    row[f"{canal.lower()}_nps"] = float(r["nps_score"]) if r["nps_score"] is not None else 0
                    total_enc += int(r["encuestas"])
                    total_prom += int(r["promotores"])
                    total_det += int(r["detractores"])
                else:
                    row[f"{canal.lower()}_count"] = 0
                    row[f"{canal.lower()}_nps"] = 0

            row["total_nps"] = round((total_prom - total_det) / total_enc * 100, 1) if total_enc > 0 else 0
            result.append(row)

        return pd.DataFrame(result)

    # ─── NPS by Entity ───────────────────────────────────────────

    def get_nps_by_entity(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        limit: int = 15,
    ) -> pd.DataFrame:
        tenant_clause = f"AND tenant_id = '{tenant}'" if tenant else ""
        date_clauses = ""
        if start:
            date_clauses += f" AND date >= '{start}'"
        if end:
            date_clauses += f" AND date <= '{end}'"

        query = text(f"""
            SELECT
                entity AS entidad,
                COUNT(*) AS encuestas,
                ROUND(AVG(score_atencion)::numeric, 2) AS avg_atencion,
                ROUND(AVG(score_asesor)::numeric, 2) AS avg_asesor,
                SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END) AS promotores,
                SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END) AS detractores,
                ROUND(
                    (SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END)
                     - SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END))::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1
                ) AS nps_score
            FROM nps_surveys
            WHERE entity IS NOT NULL AND entity != ''
                {tenant_clause} {date_clauses}
            GROUP BY entity
            ORDER BY encuestas DESC
            LIMIT :limit
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"limit": limit})

    # ─── Intent vs Canal ─────────────────────────────────────────

    def get_intent_vs_canal(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Top intents grouped by conversation canal type (Bot/Agente/Mixta)."""
        tenant_clause = f"AND m.tenant_id = '{tenant}'" if tenant else ""
        date_clauses = ""
        if start:
            date_clauses += f" AND m.date >= '{start}'"
        if end:
            date_clauses += f" AND m.date <= '{end}'"

        query = text(f"""
            WITH conv_types AS (
                SELECT conversation_id,
                    CASE
                        WHEN bool_or(is_bot) AND bool_or(is_human) THEN 'Mixta'
                        WHEN bool_or(is_human) THEN 'Agente'
                        WHEN bool_or(is_bot) THEN 'Bot'
                        ELSE 'Otro'
                    END AS canal_tipo
                FROM messages
                WHERE tenant_id = :tenant
                GROUP BY conversation_id
            ),
            top_intents AS (
                SELECT intent
                FROM messages m
                WHERE m.intent IS NOT NULL AND m.intent != ''
                    {tenant_clause} {date_clauses}
                GROUP BY intent
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            )
            SELECT
                m.intent,
                COALESCE(ct.canal_tipo, 'Otro') AS canal_tipo,
                COUNT(*) AS count
            FROM messages m
            LEFT JOIN conv_types ct ON m.conversation_id = ct.conversation_id
            WHERE m.intent IS NOT NULL AND m.intent != ''
                AND m.intent IN (SELECT intent FROM top_intents)
                {tenant_clause} {date_clauses}
            GROUP BY m.intent, ct.canal_tipo
            ORDER BY m.intent, count DESC
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"tenant": tenant or "visionamos", "limit": limit})

    # ─── Bot Fallback Trend ──────────────────────────────────────

    def get_fallback_trend(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        period: str = "month",
    ) -> pd.DataFrame:
        """Fallback count and rate grouped by period."""
        if period == "month":
            period_expr = "TO_CHAR(date, 'YYYY-MM')"
        elif period == "week":
            period_expr = "TO_CHAR(date, 'IYYY-IW')"
        else:
            period_expr = "date::text"

        tenant_clause = f"AND tenant_id = '{tenant}'" if tenant else ""
        date_clauses = ""
        if start:
            date_clauses += f" AND date >= '{start}'"
        if end:
            date_clauses += f" AND date <= '{end}'"

        query = text(f"""
            SELECT
                {period_expr} AS periodo,
                COUNT(*) AS total_mensajes,
                SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END) AS fallbacks,
                ROUND(
                    SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1
                ) AS fallback_rate
            FROM messages
            WHERE is_bot = TRUE
                {tenant_clause} {date_clauses}
            GROUP BY {period_expr}
            ORDER BY {period_expr}
        """)
        return self._exec(query)

    # ─── Fallback by Intent ──────────────────────────────────────

    def get_fallback_by_intent(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
        limit: int = 15,
    ) -> pd.DataFrame:
        """Fallback count per intent."""
        tenant_clause = f"AND tenant_id = '{tenant}'" if tenant else ""
        date_clauses = ""
        if start:
            date_clauses += f" AND date >= '{start}'"
        if end:
            date_clauses += f" AND date <= '{end}'"

        query = text(f"""
            SELECT
                COALESCE(intent, 'Sin Intent') AS intent,
                COUNT(*) AS total,
                SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END) AS fallbacks,
                ROUND(
                    SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1
                ) AS fallback_rate
            FROM messages
            WHERE is_bot = TRUE
                {tenant_clause} {date_clauses}
            GROUP BY intent
            HAVING SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END) > 0
            ORDER BY fallbacks DESC
            LIMIT :limit
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"limit": limit})

    # ─── Bot KPIs ────────────────────────────────────────────────

    def get_bot_kpis(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
    ) -> Dict[str, Any]:
        """Bot KPIs — message counts + conversation-level fallback rate."""
        t = Message.__table__
        filters = [self._tenant_filter(t, tenant), t.c.is_bot == True]
        filters += self._date_filter(t, start, end)

        with engine.connect() as conn:
            row = conn.execute(
                select(
                    func.count().label("total_bot_messages"),
                    func.count(func.distinct(t.c.contact_id)).label("unique_contacts"),
                    func.count(func.distinct(t.c.intent)).label("unique_intents"),
                ).where(and_(*filters))
            ).first()

            # Conversation-level fallback rate
            fb_row = conn.execute(text("""
                WITH conv_flags AS (
                    SELECT conversation_id,
                           BOOL_OR(is_fallback) AS had_fallback,
                           BOOL_OR(is_bot)      AS had_bot
                    FROM messages
                    WHERE conversation_id IS NOT NULL
                      AND (:tenant IS NULL OR tenant_id = :tenant)
                      AND (:start IS NULL OR date >= :start)
                      AND (:end   IS NULL OR date <= :end)
                    GROUP BY conversation_id
                )
                SELECT COUNT(*) FILTER (WHERE had_bot)                  AS bot_convs,
                       COUNT(*) FILTER (WHERE had_bot AND had_fallback) AS fb_convs
                FROM conv_flags
            """), {"tenant": tenant, "start": start, "end": end}).first()

        bot_convs = fb_row.bot_convs or 0
        fb_convs = fb_row.fb_convs or 0
        return {
            "total_bot_messages": row.total_bot_messages or 0,
            "unique_contacts": row.unique_contacts or 0,
            "unique_intents": row.unique_intents or 0,
            "total_fallbacks": fb_convs,
            "fallback_rate": round(fb_convs / bot_convs * 100, 1) if bot_convs > 0 else 0,
        }

    # ─── NPS Distribution ────────────────────────────────────────

    def get_nps_distribution(
        self, tenant: Optional[str] = None,
        start: Optional[date_type] = None, end: Optional[date_type] = None,
    ) -> pd.DataFrame:
        """NPS category counts for pie chart."""
        t = NpsSurvey.__table__
        filters = [self._tenant_filter(t, tenant)] + self._date_filter(t, start, end)
        filters.append(t.c.nps_categoria != None)

        stmt = (
            select(
                t.c.nps_categoria.label("categoria"),
                func.count().label("count"),
            )
            .where(and_(*filters))
            .group_by(t.c.nps_categoria)
            .order_by(func.count().desc())
        )
        return self._exec(stmt)
