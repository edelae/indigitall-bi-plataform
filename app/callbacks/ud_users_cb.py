"""Unified Dashboard — Control de Toques & Users callbacks."""

import logging

from dash import Input, Output, State, callback, dcc
from dash.exceptions import PreventUpdate

from app.callbacks.ud_shared import parse_range, kpi_card, empty_figure
from app.services.toques_data_service import ToquesDataService
from app.services.sms_data_service import SmsDataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-toques-kpi-row", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_toques_kpis(date_range):
    """KPIs for Ley 2300 compliance from SMS data."""
    try:
        svc = SmsDataService()
        start, end = parse_range(date_range)
        kpis = svc.get_sms_kpis(start_date=start, end_date=end)
        return [
            kpi_card("Envios SMS", kpis["total_enviados"], "bi-phone", md=3),
            kpi_card("Telefono Unicos", kpis["unique_phones"], "bi-people", "info", md=3),
            kpi_card("Campanas", kpis["campanas"], "bi-megaphone", "warning", md=3),
            kpi_card("Entrega", f"{kpis['delivery_rate']}%", "bi-check2-circle", "success", md=3),
        ]
    except Exception:
        log.exception("Error loading toques KPIs")
        return [
            kpi_card("Envios SMS", 0, "bi-phone", md=3),
            kpi_card("Telefono Unicos", 0, "bi-people", "info", md=3),
            kpi_card("Campanas", 0, "bi-megaphone", "warning", md=3),
            kpi_card("Entrega", "0%", "bi-check2-circle", "success", md=3),
        ]


@callback(
    Output("ud-toques-hour-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_toques_hour_chart(date_range):
    """SMS sends by hour — useful for Ley 2300 schedule compliance."""
    try:
        svc = SmsDataService()
        start, end = parse_range(date_range)
        df = svc.get_heatmap_data(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Sin datos de envios por hora")
        hourly = df.groupby("hora", as_index=False)["value"].sum()
        hourly.columns = ["hour", "count"]
        return ChartService().create_hourly_distribution_chart(hourly)
    except Exception:
        log.exception("Error loading toques hour chart")
        return empty_figure("Error")


@callback(
    Output("ud-users-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("ud-users-threshold", "value"),
)
def load_ud_users_kpis(date_range, threshold):
    threshold = threshold or 4
    try:
        svc = ToquesDataService()
        df = svc.get_users_high_volume(threshold=threshold, limit=10000)
        total_users = len(df)
        total_toques = int(df["total_toques"].sum()) if not df.empty else 0
    except Exception:
        log.exception("Error loading Users KPIs")
        total_users, total_toques = 0, 0

    return [
        kpi_card("Usuarios Sobre-tocados", total_users, "bi-exclamation-octagon", "danger"),
        kpi_card("Total Toques", total_toques, "bi-graph-up-arrow", "warning"),
    ]


@callback(
    Output("ud-users-table", "data"),
    Output("ud-users-table", "columns"),
    Input("ud-date-store", "data"),
    Input("ud-users-threshold", "value"),
)
def load_ud_users_table(date_range, threshold):
    threshold = threshold or 4
    try:
        svc = ToquesDataService()
        df = svc.get_users_high_volume(threshold=threshold, limit=200)
        if df.empty:
            return [], []
        col_map = {
            "telefono": "Telefono", "canal": "Canal",
            "proyecto_cuenta": "Proyecto", "total_toques": "Toques",
            "total_clicks": "Clicks", "dias_activos": "Dias Activos",
        }
        columns = [{"name": col_map.get(c, c), "id": c} for c in df.columns if c in col_map]
        return df.to_dict("records"), columns
    except Exception:
        log.exception("Error loading Users table")
        return [], []


@callback(
    Output("ud-users-download-csv", "data"),
    Input("ud-users-export-csv-btn", "n_clicks"),
    State("ud-users-threshold", "value"),
    prevent_initial_call=True,
)
def export_ud_users_csv(n_clicks, threshold):
    if not n_clicks:
        raise PreventUpdate
    threshold = threshold or 4
    svc = ToquesDataService()
    df = svc.get_users_high_volume(threshold=threshold, limit=10000)
    if df.empty:
        raise PreventUpdate
    return dcc.send_data_frame(df.to_csv, "usuarios_sobre_tocados.csv", index=False)
