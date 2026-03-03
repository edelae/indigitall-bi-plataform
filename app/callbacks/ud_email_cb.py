"""Unified Dashboard — Email tab callbacks."""

import logging

from dash import Input, Output, callback
import dash_bootstrap_components as dbc

from app.callbacks.ud_shared import parse_range, kpi_card, no_data_alert, empty_figure
from app.services.toques_data_service import ToquesDataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-email-kpi-row", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_email_kpis(date_range):
    try:
        svc = ToquesDataService()
        start, end = parse_range(date_range)
        kpis = svc.get_email_kpis(start_date=start, end_date=end)
        has_data = kpis["total_enviados"] > 0
    except Exception:
        log.exception("Error loading Email KPIs")
        kpis = {"open_rate": 0, "ctr": 0, "pct_rebotes": 0,
                "pct_bloqueados": 0, "pct_spam": 0, "pct_desuscritos": 0}
        has_data = False

    cards = [
        kpi_card("% Open Rate", f"{kpis['open_rate']}%", "bi-envelope-open", "primary", md=2),
        kpi_card("% CTR", f"{kpis['ctr']}%", "bi-cursor", "success", md=2),
        kpi_card("% Rebotes", f"{kpis['pct_rebotes']}%", "bi-exclamation-triangle", "warning", md=2),
        kpi_card("% Bloqueados", f"{kpis['pct_bloqueados']}%", "bi-slash-circle", "danger", md=2),
        kpi_card("% Spam", f"{kpis['pct_spam']}%", "bi-shield-exclamation", "danger", md=2),
        kpi_card("% Desuscritos", f"{kpis['pct_desuscritos']}%", "bi-person-dash", "warning", md=2),
    ]
    if not has_data:
        return [dbc.Col(no_data_alert("Email"), md=12)] + cards
    return cards


@callback(
    Output("ud-email-engagement-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_email_engagement(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_email_engagement_trend(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Engagement Email")
        return charts.create_multi_line_chart(
            df, "", "date", ["entregados", "abiertos", "clicks"],
            {"entregados": "Entregados", "abiertos": "Abiertos", "clicks": "Clicks"},
        )
    except Exception:
        log.exception("Error loading Email engagement")
        return empty_figure("Engagement Email")


@callback(
    Output("ud-email-errors-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_email_errors(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_email_error_breakdown(start_date=start, end_date=end)
        if df.empty or df["cantidad"].sum() == 0:
            return empty_figure("Desglose de Errores")
        return charts.create_bar_chart(df, "", "tipo", "cantidad")
    except Exception:
        log.exception("Error loading Email errors")
        return empty_figure("Desglose de Errores")


@callback(
    Output("ud-email-heatmap-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_email_heatmap(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        df = svc.get_heatmap_data(channels=["Email"])
        if df.empty:
            return empty_figure("Mapa de Calor Email")
        return charts.create_heatmap(df, "", "hora", "dia_semana", "value")
    except Exception:
        log.exception("Error loading Email heatmap")
        return empty_figure("Mapa de Calor Email")


@callback(
    Output("ud-email-ranking-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_email_ranking(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        df = svc.get_email_campaigns_by_engagement(limit=10)
        if df.empty:
            return empty_figure("Sin datos de campanas")
        return charts.create_ranking_bar_chart(
            df, "", "campana_nombre", "open_rate", secondary_col="ctr",
        )
    except Exception:
        log.exception("Error loading Email ranking")
        return empty_figure("Sin datos de campanas")
