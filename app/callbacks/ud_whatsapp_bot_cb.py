"""Unified Dashboard — WhatsApp/Bot merged tab callbacks."""

import logging

from dash import Input, Output, State, callback, dcc
from dash.exceptions import PreventUpdate

from app.callbacks.ud_shared import parse_range, kpi_card, empty_figure
from app.services.data_service import DataService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-wa-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_kpis(date_range, tenant):
    try:
        svc = DataService()
        start, end = parse_range(date_range)
        kpis = svc.get_wa_kpis(tenant_filter=tenant, start_date=start, end_date=end)
    except Exception:
        log.exception("Error loading WA KPIs")
        kpis = {"total_messages": 0, "unique_contacts": 0, "fallback_rate": 0,
                "avg_wait_seconds": 0, "delivery_rate": 0, "bot_resolution_pct": 0}
    return [
        kpi_card("Total Mensajes", kpis["total_messages"], "bi-chat-dots", md=2),
        kpi_card("Contactos", kpis["unique_contacts"], "bi-people", "info", md=2),
        kpi_card("Fallback", f"{kpis['fallback_rate']}%", "bi-exclamation-triangle", "warning", md=2),
        kpi_card("T. Espera", f"{kpis['avg_wait_seconds']}s", "bi-clock", "info", md=2),
        kpi_card("Entrega", f"{kpis['delivery_rate']}%", "bi-check2-circle", "success", md=2),
        kpi_card("Bot", f"{kpis['bot_resolution_pct']}%", "bi-robot", "primary", md=2),
    ]


@callback(
    Output("ud-wa-messages-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_messages_trend(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_messages_over_time_filtered(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Mensajes por Dia")
        return charts.create_chart(df, "area", "", "date", "count")
    except Exception:
        log.exception("Error loading WA messages trend")
        return empty_figure("Mensajes por Dia")


@callback(
    Output("ud-wa-direction-pie-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_direction(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_direction_breakdown_filtered(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Direccion de Mensajes")
        return charts.create_pie_chart(df, "", "direction", "count")
    except Exception:
        log.exception("Error loading WA direction")
        return empty_figure("Direccion de Mensajes")


@callback(
    Output("ud-wa-fallback-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_fallback_trend(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_fallback_trend_filtered(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty or "fallback_rate" not in df.columns:
            return empty_figure("Tendencia Fallback")
        return charts.create_line_chart_with_target(
            df, "", "date", "fallback_rate",
            target_value=15, target_label="Meta",
        )
    except Exception:
        log.exception("Error loading WA fallback trend")
        return empty_figure("Tendencia Fallback")


@callback(
    Output("ud-wa-top-intents-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_top_intents(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_top_intents_filtered(
            tenant_filter=tenant, start_date=start, end_date=end, limit=10,
        )
        return charts.create_intent_chart(df)
    except Exception:
        log.exception("Error loading WA intents")
        return empty_figure("Top Intenciones")


@callback(
    Output("ud-wa-status-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_status(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_message_status_distribution(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Estado de Entrega")
        return charts.create_bar_chart(df, "", "status", "count")
    except Exception:
        log.exception("Error loading WA status")
        return empty_figure("Estado de Entrega")


@callback(
    Output("ud-wa-content-type-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_content_type(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_content_type_breakdown(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Tipos de Contenido")
        return charts.create_bar_chart(df, "", "content_type", "count")
    except Exception:
        log.exception("Error loading WA content types")
        return empty_figure("Tipos de Contenido")


@callback(
    Output("ud-wa-heatmap-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_heatmap(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_messages_heatmap(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Mapa de Calor WhatsApp")
        return charts.create_heatmap(df, "", "hora", "dia_semana", "value")
    except Exception:
        log.exception("Error loading WA heatmap")
        return empty_figure("Mapa de Calor WhatsApp")


@callback(
    Output("ud-wa-bot-vs-human-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_bot_vs_human(date_range, tenant):
    try:
        svc, charts = DataService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_bot_resolution_summary(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Bot vs Agente")
        return charts.create_pie_chart(df, "", "category", "count")
    except Exception:
        log.exception("Error loading WA bot vs human")
        return empty_figure("Bot vs Agente")


@callback(
    Output("ud-wa-detail-table", "data"),
    Output("ud-wa-detail-table", "columns"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_detail_table(date_range, tenant):
    try:
        svc = DataService()
        start, end = parse_range(date_range)
        df = svc.get_messages_page(
            tenant_filter=tenant, start_date=start, end_date=end,
            page=0, page_size=100,
        )
        if df.empty:
            return [], []
        col_map = {
            "date": "Fecha", "hour": "Hora", "direction": "Direccion",
            "content_type": "Tipo", "status": "Estado",
            "contact_name": "Contacto", "intent": "Intencion",
            "is_fallback": "Fallback",
        }
        columns = [{"name": col_map.get(c, c), "id": c} for c in df.columns if c in col_map]
        return df.to_dict("records"), columns
    except Exception:
        log.exception("Error loading WA detail table")
        return [], []


@callback(
    Output("ud-wa-download-csv", "data"),
    Input("ud-wa-export-csv-btn", "n_clicks"),
    State("ud-date-store", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def export_ud_wa_csv(n_clicks, date_range, tenant):
    if not n_clicks:
        raise PreventUpdate
    svc = DataService()
    start, end = parse_range(date_range)
    df = svc.get_messages_page(
        tenant_filter=tenant, start_date=start, end_date=end,
        page=0, page_size=5000,
    )
    if df.empty:
        raise PreventUpdate
    return dcc.send_data_frame(df.to_csv, "whatsapp_mensajes.csv", index=False)
