"""Unified Dashboard — WhatsApp Atendimiento sub-tab callbacks."""

import logging

from dash import Input, Output, callback

from app.callbacks.ud_shared import parse_range, kpi_card_with_delta, empty_figure
from app.services.contact_center_service import ContactCenterService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-wa-atend-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_atend_kpis(date_range, tenant):
    """KPIs: total conversations, bot-only, human-only, escalation rate."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        counts = svc.get_conversation_type_counts(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
    except Exception:
        log.exception("Error loading WA atendimiento KPIs")
        counts = {"total": 0, "bot_only": 0, "human_only": 0, "mixed": 0}

    total = counts["total"]
    escalation_pct = round(counts["mixed"] / total * 100, 1) if total > 0 else 0

    return [
        kpi_card_with_delta(
            "Conversaciones", total, None, "bi-chat-dots", md=3,
        ),
        kpi_card_with_delta(
            "Solo Bot", counts["bot_only"], None, "bi-robot", "info", md=3,
        ),
        kpi_card_with_delta(
            "Solo Humano", counts["human_only"], None, "bi-person", "success", md=3,
        ),
        kpi_card_with_delta(
            "Escalacion", f"{escalation_pct}%", None, "bi-arrow-up-right", "warning", md=3,
        ),
    ]


@callback(
    Output("ud-wa-atend-type-pie", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_atend_type_pie(date_range, tenant):
    """Pie chart for conversation type distribution."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        counts = svc.get_conversation_type_counts(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if counts["total"] == 0:
            return empty_figure("Sin datos de conversaciones")

        import pandas as pd
        df = pd.DataFrame([
            {"tipo": "Solo Bot", "count": counts["bot_only"]},
            {"tipo": "Solo Humano", "count": counts["human_only"]},
            {"tipo": "Mixta", "count": counts["mixed"]},
        ])
        df = df[df["count"] > 0]
        if df.empty:
            return empty_figure("Sin datos")
        return ChartService().create_pie_chart(df, "", "tipo", "count")
    except Exception:
        log.exception("Error loading WA atendimiento type pie")
        return empty_figure("Error")


@callback(
    Output("ud-wa-atend-type-trend", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_atend_type_trend(date_range, tenant):
    """Stacked area for conversation type trend."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        df = svc.get_conversation_type_trend(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Sin datos de tendencia")
        return ChartService().create_stacked_area_chart(
            df, "", "date", ["bot_only", "human_only", "mixed"],
            labels={"bot_only": "Solo Bot", "human_only": "Solo Humano", "mixed": "Mixta"},
            colors=["#1E88E5", "#76C043", "#FFC107"],
        )
    except Exception:
        log.exception("Error loading WA atendimiento type trend")
        return empty_figure("Error")


@callback(
    Output("ud-wa-atend-escalation-gauge", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_atend_escalation(date_range, tenant):
    """Gauge showing escalation rate (mixed / total conversations)."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        counts = svc.get_conversation_type_counts(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        total = counts["total"]
        rate = round(counts["mixed"] / total * 100, 1) if total > 0 else 0
        return ChartService().create_gauge_chart(
            rate, "Tasa Escalacion", target=20,
        )
    except Exception:
        log.exception("Error loading WA escalation gauge")
        return empty_figure("Error")
