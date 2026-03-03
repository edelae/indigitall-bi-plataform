"""Unified Dashboard — WhatsApp Humano sub-tab callbacks."""

import logging

from dash import Input, Output, State, callback, dcc
from dash.exceptions import PreventUpdate

from app.callbacks.ud_shared import parse_range, kpi_card, empty_figure
from app.services.contact_center_service import ContactCenterService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


@callback(
    Output("ud-wa-hum-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_kpis(date_range, tenant):
    """KPIs: conversations, agents, FCR, avg FRT, avg handle time."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        kpis = svc.get_cc_kpis_expanded(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
    except Exception:
        log.exception("Error loading WA humano KPIs")
        kpis = {
            "total_conversations": 0, "active_agents": 0, "fcr_rate": 0,
            "avg_frt_seconds": 0, "avg_handle_seconds": 0,
        }

    frt_min = round(kpis["avg_frt_seconds"] / 60, 1) if kpis["avg_frt_seconds"] else 0
    handle_min = round(kpis["avg_handle_seconds"] / 60, 1) if kpis["avg_handle_seconds"] else 0

    return [
        kpi_card("Conversaciones", kpis["total_conversations"], "bi-chat-square-dots", md=2),
        kpi_card("Agentes", kpis["active_agents"], "bi-people", "info", md=2),
        kpi_card("FCR", f"{kpis['fcr_rate']}%", "bi-check-circle", "success", md=2),
        kpi_card("FRT Prom", f"{frt_min} min", "bi-clock-history", "warning", md=3),
        kpi_card("T. Gestion", f"{handle_min} min", "bi-stopwatch", "primary", md=3),
    ]


@callback(
    Output("ud-wa-hum-frt-trend", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_frt_trend(date_range, tenant):
    """FRT trend with 1-minute target line."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_first_response_time_trend(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Tendencia FRT")
        df["avg_frt_minutes"] = (df["avg_frt_seconds"] / 60).round(1)
        return charts.create_line_chart_with_target(
            df, "", "date", "avg_frt_minutes",
            target_value=1.0, target_label="Meta FRT",
        )
    except Exception:
        log.exception("Error loading WA humano FRT trend")
        return empty_figure("Tendencia FRT")


@callback(
    Output("ud-wa-hum-handle-trend", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_handle_trend(date_range, tenant):
    """Handle time trend with 5-minute target."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_handle_time_trend(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Tendencia T. Gestion")
        df["avg_handle_minutes"] = (df["avg_handle_seconds"] / 60).round(1)
        return charts.create_line_chart_with_target(
            df, "", "date", "avg_handle_minutes",
            target_value=5.0, target_label="Meta Gestion",
        )
    except Exception:
        log.exception("Error loading WA humano handle trend")
        return empty_figure("Tendencia T. Gestion")


@callback(
    Output("ud-wa-hum-conv-trend", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_conv_trend(date_range, tenant):
    """Daily conversation volume area chart."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_conversations_over_time(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Conversaciones por Dia")
        return charts.create_chart(df, "area", "", "date", "count")
    except Exception:
        log.exception("Error loading WA humano conv trend")
        return empty_figure("Conversaciones por Dia")


@callback(
    Output("ud-wa-hum-close-reasons", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_close_reasons(date_range, tenant):
    """Close reason distribution."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_close_reasons(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Razones de Cierre")
        return charts.create_pie_chart(df, "", "reason", "count")
    except Exception:
        log.exception("Error loading WA humano close reasons")
        return empty_figure("Razones de Cierre")


@callback(
    Output("ud-wa-hum-dead-time", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_dead_time(date_range, tenant):
    """Dead time trend from analytics schema."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_dead_time_trend(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Tiempo Muerto — Sin datos")
        df["avg_dead_minutes"] = (df["avg_dead_time_seconds"] / 60).round(1)
        return charts.create_chart(df, "line", "", "date", "avg_dead_minutes")
    except Exception:
        log.exception("Error loading WA humano dead time")
        return empty_figure("Tiempo Muerto")


@callback(
    Output("ud-wa-hum-coverage-pie", "figure"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_coverage(tenant):
    """Pie chart: managed vs unmanaged contacts."""
    try:
        import pandas as pd
        svc = ContactCenterService()
        data = svc.get_managed_vs_unmanaged(tenant_filter=tenant)
        if data["total"] == 0:
            return empty_figure("Sin datos de contactos")
        df = pd.DataFrame([
            {"tipo": "Atendidos", "count": data["managed"]},
            {"tipo": "Sin atencion", "count": data["unmanaged"]},
        ])
        df = df[df["count"] > 0]
        if df.empty:
            return empty_figure("Sin datos")
        return ChartService().create_pie_chart(df, "", "tipo", "count")
    except Exception:
        log.exception("Error loading WA humano coverage")
        return empty_figure("Cobertura")


@callback(
    Output("ud-wa-hum-heatmap", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_heatmap(date_range, tenant):
    """Hourly conversation distribution bar chart."""
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_hourly_queue(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return empty_figure("Conversaciones por Hora")
        return charts.create_hourly_distribution_chart(df)
    except Exception:
        log.exception("Error loading WA humano heatmap")
        return empty_figure("Conversaciones por Hora")


@callback(
    Output("ud-wa-hum-agent-table", "data"),
    Output("ud-wa-hum-agent-table", "columns"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_wa_hum_agent_table(date_range, tenant):
    """Agent performance data table."""
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        df = svc.get_agent_performance_table(
            tenant_filter=tenant, start_date=start, end_date=end,
        )
        if df.empty:
            return [], []
        col_map = {
            "agent_id": "Agente", "conversations": "Conversaciones",
            "contacts": "Contactos", "avg_frt": "FRT Prom (s)",
            "avg_handle": "T. Gestion (s)",
        }
        columns = [{"name": col_map.get(c, c), "id": c} for c in df.columns if c in col_map]
        return df.to_dict("records"), columns
    except Exception:
        log.exception("Error loading WA humano agent table")
        return [], []


@callback(
    Output("ud-wa-hum-download-csv", "data"),
    Input("ud-wa-hum-export-csv-btn", "n_clicks"),
    State("ud-date-store", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def export_ud_wa_hum_csv(n_clicks, date_range, tenant):
    """Export agent table as CSV."""
    if not n_clicks:
        raise PreventUpdate
    svc = ContactCenterService()
    start, end = parse_range(date_range)
    df = svc.get_agent_performance_table(
        tenant_filter=tenant, start_date=start, end_date=end, limit=100,
    )
    if df.empty:
        raise PreventUpdate
    return dcc.send_data_frame(df.to_csv, "agentes_humanos.csv", index=False)
