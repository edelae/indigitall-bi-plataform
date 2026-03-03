"""Unified Dashboard — Push tab callbacks."""

import logging

from dash import Input, Output, callback
import dash_bootstrap_components as dbc

from app.callbacks.ud_shared import parse_range, kpi_card, no_data_alert, empty_figure
from app.services.toques_data_service import ToquesDataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-push-kpi-row", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_push_kpis(date_range):
    try:
        svc = ToquesDataService()
        start, end = parse_range(date_range)
        kpis = svc.get_kpis(channels=["Push"], start_date=start, end_date=end)
        env = kpis["total_enviados"]
        chunks = kpis["total_chunks"]
        has_data = env > 0
        tasa_entrega = round(chunks / env * 100, 2) if env > 0 else 0
    except Exception:
        log.exception("Error loading Push KPIs")
        env, chunks, tasa_entrega, has_data = 0, 0, 0, False
        kpis = {"ctr_promedio": 0}

    cards = [
        kpi_card("Total Enviados", env, "bi-send"),
        kpi_card("Total Entregados", chunks, "bi-check2-circle", "success"),
        kpi_card("CTR", f"{kpis['ctr_promedio']}%", "bi-cursor", "primary"),
        kpi_card("Tasa Entrega", f"{tasa_entrega}%", "bi-arrow-right-circle", "info"),
    ]
    if not has_data:
        return [dbc.Col(no_data_alert("Push"), md=12)] + cards
    return cards


@callback(
    Output("ud-push-trend-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_push_trend(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_sends_clicks_ctr(channels=["Push"], start_date=start, end_date=end)
        if df.empty or df["enviados"].sum() == 0:
            return empty_figure("Enviados vs Clicks Push")
        return charts.create_combo_chart(
            df, "", "date",
            y1_cols=["enviados", "clicks"],
            y1_labels={"enviados": "Enviados", "clicks": "Clicks"},
            y2_cols=["ctr"],
            y2_labels={"ctr": "CTR %"},
        )
    except Exception:
        log.exception("Error loading Push trend")
        return empty_figure("Enviados vs Clicks Push")


@callback(
    Output("ud-push-heatmap-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_push_heatmap(date_range):
    try:
        svc, charts = ToquesDataService(), ChartService()
        df = svc.get_heatmap_data(channels=["Push"])
        if df.empty:
            return empty_figure("Mapa de Calor Push")
        return charts.create_heatmap(df, "", "hora", "dia_semana", "value")
    except Exception:
        log.exception("Error loading Push heatmap")
        return empty_figure("Mapa de Calor Push")
