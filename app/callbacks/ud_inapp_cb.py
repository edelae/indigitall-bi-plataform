"""Unified Dashboard — In App/Web tab callbacks."""

import logging

from dash import Input, Output, callback
import dash_bootstrap_components as dbc

from app.callbacks.ud_shared import parse_range, kpi_card, no_data_alert, empty_figure
from app.services.toques_data_service import ToquesDataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-inapp-kpi-row", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_inapp_kpis(date_range):
    try:
        svc = ToquesDataService()
        start, end = parse_range(date_range)
        kpis = svc.get_inapp_kpis(start_date=start, end_date=end)
        has_data = kpis["total_impresiones"] > 0
    except Exception:
        log.exception("Error loading InApp KPIs")
        kpis = {"total_impresiones": 0, "total_clicks": 0, "ctr": 0, "total_conversiones": 0}
        has_data = False

    cards = [
        kpi_card("Impresiones", kpis["total_impresiones"], "bi-eye"),
        kpi_card("Clicks", kpis["total_clicks"], "bi-cursor", "primary"),
        kpi_card("CTR", f"{kpis['ctr']}%", "bi-percent", "success"),
        kpi_card("Conversiones", kpis["total_conversiones"], "bi-trophy", "warning"),
    ]
    if not has_data:
        return [dbc.Col(no_data_alert("In App/Web"), md=12)] + cards
    return cards


@callback(
    Output("ud-inapp-engagement-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_inapp_engagement(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_inapp_engagement_trend(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Impresiones vs Clicks")
        return charts.create_multi_line_chart(
            df, "", "date", ["impresiones", "clicks"],
            {"impresiones": "Impresiones", "clicks": "Clicks"},
        )
    except Exception:
        log.exception("Error loading InApp engagement")
        return empty_figure("Impresiones vs Clicks")


@callback(
    Output("ud-inapp-funnel-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_inapp_funnel(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_inapp_conversion_funnel(start_date=start, end_date=end)
        if df.empty or df["cantidad"].sum() == 0:
            return empty_figure("Funnel de Conversion")
        return charts.create_bar_chart(df, "", "etapa", "cantidad")
    except Exception:
        log.exception("Error loading InApp funnel")
        return empty_figure("Funnel de Conversion")
