"""Unified Dashboard — SMS tab callbacks (all from sms_envios)."""

import logging

from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app.callbacks.ud_shared import parse_range, kpi_card, no_data_alert, empty_figure
from app.services.sms_data_service import SmsDataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-sms-kpi-row", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_kpis(date_range):
    try:
        svc = SmsDataService()
        start, end = parse_range(date_range)
        kpis = svc.get_sms_kpis(start_date=start, end_date=end)
        has_data = kpis["total_enviados"] > 0
    except Exception:
        log.exception("Error loading SMS KPIs")
        kpis = {"total_enviados": 0, "total_clicks": 0, "total_chunks": 0,
                "ctr": 0, "campanas": 0, "delivery_rate": 0}
        has_data = False

    cards = [
        kpi_card("Enviados", kpis["total_enviados"], "bi-send", md=2),
        kpi_card("Clicks", kpis["total_clicks"], "bi-cursor", md=2),
        kpi_card("Chunks", kpis["total_chunks"], "bi-stack", md=2),
        kpi_card("CTR", f"{kpis['ctr']}%", "bi-percent", "success", md=2),
        kpi_card("Campanas", kpis["campanas"], "bi-megaphone", "info", md=2),
        kpi_card("Entrega", f"{kpis['delivery_rate']}%", "bi-check2-circle", "primary", md=2),
    ]
    if not has_data:
        return [dbc.Col(no_data_alert("SMS"), md=12)] + cards
    return cards


@callback(
    Output("ud-sms-sends-chunks-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_sends_chunks(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_sends_vs_chunks_trend(start_date=start, end_date=end)
        if df.empty or df["enviados"].sum() == 0:
            return empty_figure("Enviados vs Chunks")
        return charts.create_multi_line_chart(
            df, "", "date", ["enviados", "chunks"],
            {"enviados": "Enviados", "chunks": "Chunks"},
        )
    except Exception:
        log.exception("Error loading SMS sends vs chunks")
        return empty_figure("Enviados vs Chunks")


@callback(
    Output("ud-sms-sends-clicks-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_sends_clicks(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_sends_clicks_ctr_trend(start_date=start, end_date=end)
        if df.empty or df["enviados"].sum() == 0:
            return empty_figure("Enviados vs Clicks vs CTR")
        return charts.create_combo_chart(
            df, "", "date",
            y1_cols=["enviados", "clicks"],
            y1_labels={"enviados": "Enviados", "clicks": "Clicks"},
            y2_cols=["ctr"],
            y2_labels={"ctr": "CTR %"},
        )
    except Exception:
        log.exception("Error loading SMS sends vs clicks")
        return empty_figure("Enviados vs Clicks vs CTR")


@callback(
    Output("ud-sms-heatmap-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_heatmap(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_heatmap_data(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Mapa de Calor SMS")
        return charts.create_heatmap(df, "", "hora", "dia_semana", "value")
    except Exception:
        log.exception("Error loading SMS heatmap")
        return empty_figure("Mapa de Calor SMS")


@callback(
    Output("ud-sms-ranking-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_ranking(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_campaign_ranking(start_date=start, end_date=end, limit=10)
        if df.empty:
            return empty_figure("Sin datos de campanas")
        return charts.create_ranking_bar_chart(
            df, "", "campana_nombre", "total_enviados", secondary_col="ctr",
        )
    except Exception:
        log.exception("Error loading SMS ranking")
        return empty_figure("Sin datos de campanas")


@callback(
    Output("ud-sms-ranking-ctr-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_ranking_ctr(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_campaign_ranking_by_ctr(start_date=start, end_date=end, limit=10)
        if df.empty:
            return empty_figure("Sin campanas con >100 envios")
        return charts.create_ranking_bar_chart(
            df, "", "campana_nombre", "ctr", secondary_col="total_enviados",
        )
    except Exception:
        log.exception("Error loading SMS ranking by CTR")
        return empty_figure("Sin datos de campanas")


@callback(
    Output("ud-sms-delivery-trend-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_delivery_trend(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_delivery_rate_trend(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Tendencia de Entrega")
        return charts.create_line_chart_with_target(
            df, "", "date", "rate",
            target_value=95, target_label="Meta",
        )
    except Exception:
        log.exception("Error loading SMS delivery trend")
        return empty_figure("Tendencia de Entrega")


@callback(
    Output("ud-sms-error-pie-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_error_pie(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_status_breakdown(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Estado de Envio")
        return charts.create_bar_chart(df, "", "status", "count")
    except Exception:
        log.exception("Error loading SMS status breakdown")
        return empty_figure("Estado de Envio")


@callback(
    Output("ud-sms-type-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_type(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_sending_type_breakdown(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Tipo de Envio")
        return charts.create_bar_chart(df, "", "sending_type", "count")
    except Exception:
        log.exception("Error loading SMS type")
        return empty_figure("Tipo de Envio")


@callback(
    Output("ud-sms-network-chart", "figure"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_network(date_range):
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_network_breakdown(start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Red Operadora")
        return charts.create_ranking_bar_chart(
            df, "", "network_name", "count", secondary_col="delivery_rate",
        )
    except Exception:
        log.exception("Error loading SMS network")
        return empty_figure("Red Operadora")


@callback(
    Output("ud-sms-detail-table", "data"),
    Output("ud-sms-detail-table", "columns"),
    Output("ud-sms-detail-total", "children"),
    Input("ud-date-store", "data"),
)
def load_ud_sms_detail_table(date_range):
    try:
        svc = SmsDataService()
        start, end = parse_range(date_range)
        df, total = svc.get_detail_page(start_date=start, end_date=end, page=0, page_size=200)
        if df.empty:
            return [], [], "0 registros"
        col_map = {
            "fecha": "Fecha", "campaign_name": "Campana", "phone": "Telefono",
            "status": "Estado", "network_name": "Red", "total_chunks": "Chunks",
            "clicks": "Clicks", "error_description": "Error",
        }
        columns = [{"name": col_map.get(c, c), "id": c} for c in df.columns if c in col_map]
        return df.to_dict("records"), columns, f"{total:,} registros"
    except Exception:
        log.exception("Error loading SMS detail table")
        return [], [], "Error"


@callback(
    Output("ud-sms-download-csv", "data"),
    Input("ud-sms-export-csv-btn", "n_clicks"),
    State("ud-date-store", "data"),
    prevent_initial_call=True,
)
def export_ud_sms_csv(n_clicks, date_range):
    if not n_clicks:
        raise PreventUpdate
    svc = SmsDataService()
    start, end = parse_range(date_range)
    df, _ = svc.get_detail_page(start_date=start, end_date=end, page=0, page_size=5000)
    if df.empty:
        raise PreventUpdate
    return dcc.send_data_frame(df.to_csv, "sms_detalle.csv", index=False)


@callback(
    Output("ud-sms-drill-container", "children"),
    Input("ud-sms-drill-store", "data"),
    Input("ud-date-store", "data"),
)
def render_ud_sms_drill(drill_state, date_range):
    level = (drill_state or {}).get("level", "day")
    try:
        svc, charts = SmsDataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_drill_data(start_date=start, end_date=end, granularity=level)
        if df.empty:
            return dcc.Graph(figure=empty_figure("Sin datos"), config={"displayModeBar": False})
        fig = charts.create_bar_chart(df, "", "period", "total")
        return dcc.Graph(figure=fig, config={"displayModeBar": False})
    except Exception:
        log.exception("Error loading SMS drill")
        return dcc.Graph(figure=empty_figure("Error"), config={"displayModeBar": False})
