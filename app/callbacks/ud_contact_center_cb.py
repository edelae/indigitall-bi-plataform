"""Unified Dashboard — Contact Center tab callbacks (expanded)."""

import logging

from dash import Input, Output, callback, dcc

from app.callbacks.ud_shared import parse_range, kpi_card, empty_figure
from app.services.contact_center_service import ContactCenterService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)


# ==================== KPIs ====================

@callback(
    Output("ud-cc-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_kpis(date_range, tenant):
    try:
        svc = ContactCenterService()
        start, end = parse_range(date_range)
        kpis = svc.get_cc_kpis_expanded(tenant_filter=tenant, start_date=start, end_date=end)
    except Exception:
        log.exception("Error loading expanded CC KPIs")
        kpis = {"total_conversations": 0, "active_agents": 0, "fcr_rate": 0,
                "avg_frt_seconds": 0, "avg_handle_seconds": 0, "nps": 0}

    frt_min = round(kpis["avg_frt_seconds"] / 60, 1) if kpis["avg_frt_seconds"] else 0
    handle_min = round(kpis["avg_handle_seconds"] / 60, 1) if kpis["avg_handle_seconds"] else 0
    return [
        kpi_card("Conversaciones", kpis["total_conversations"], "bi-chat-square-dots", md=2),
        kpi_card("Agentes", kpis["active_agents"], "bi-people", "info", md=2),
        kpi_card("FCR", f"{kpis['fcr_rate']}%", "bi-check-circle", "success", md=2),
        kpi_card("FRT Prom", f"{frt_min} min", "bi-clock-history", "warning", md=2),
        kpi_card("T. Gestion", f"{handle_min} min", "bi-stopwatch", "primary", md=2),
        kpi_card("NPS", f"{kpis['nps']}", "bi-star", "info", md=2),
    ]


# ==================== Trends ====================

@callback(
    Output("ud-cc-conv-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_conv_trend(date_range, tenant):
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_conversations_over_time(tenant_filter=tenant, start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Conversaciones por Dia")
        return charts.create_chart(df, "area", "", "date", "count")
    except Exception:
        log.exception("Error loading CC conv trend")
        return empty_figure("Conversaciones por Dia")


@callback(
    Output("ud-cc-frt-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_frt_trend(date_range, tenant):
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
        log.exception("Error loading CC FRT trend")
        return empty_figure("Tendencia FRT")


@callback(
    Output("ud-cc-handle-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_handle_trend(date_range, tenant):
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
        log.exception("Error loading CC handle trend")
        return empty_figure("Tendencia T. Gestion")


# ==================== Distribution & Reasons ====================

@callback(
    Output("ud-cc-wait-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_wait(date_range, tenant):
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_wait_time_distribution(tenant_filter=tenant, start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Distribucion de Espera")
        return charts.create_bar_chart(df, "", "bucket", "count")
    except Exception:
        log.exception("Error loading CC wait distribution")
        return empty_figure("Distribucion de Espera")


@callback(
    Output("ud-cc-close-reasons-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_close_reasons(date_range, tenant):
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_close_reasons(tenant_filter=tenant, start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Razones de Cierre")
        return charts._create_horizontal_bar_chart(df, "", "reason", "count")
    except Exception:
        log.exception("Error loading CC close reasons")
        return empty_figure("Razones de Cierre")


@callback(
    Output("ud-cc-nps-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_nps(date_range, tenant):
    return empty_figure("NPS — Proximamente")


# ==================== Agent Table (expanded) ====================

@callback(
    Output("ud-cc-agent-table", "data"),
    Output("ud-cc-agent-table", "columns"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_agent_table(date_range, tenant):
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
        log.exception("Error loading CC agent table")
        return [], []


# ==================== Hourly ====================

@callback(
    Output("ud-cc-hourly-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_cc_hourly(date_range, tenant):
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_hourly_queue(tenant_filter=tenant, start_date=start, end_date=end)
        if df.empty:
            return empty_figure("Conversaciones por Hora")
        return charts.create_hourly_distribution_chart(df)
    except Exception:
        log.exception("Error loading CC hourly")
        return empty_figure("Conversaciones por Hora")


# ==================== Drill-down ====================

@callback(
    Output("ud-cc-drill-container", "children"),
    Input("ud-cc-drill-store", "data"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def render_ud_cc_drill(drill_state, date_range, tenant):
    level = (drill_state or {}).get("level", "month")
    try:
        svc, charts = ContactCenterService(), ChartService()
        start, end = parse_range(date_range)
        df = svc.get_conversation_drill_data(
            tenant_filter=tenant, start_date=start, end_date=end, granularity=level,
        )
        if df.empty:
            return empty_figure("Sin datos")
        return dcc.Graph(
            figure=charts.create_bar_chart(df, "", "period", "count"),
            config={"displayModeBar": False},
        )
    except Exception:
        log.exception("Error loading CC drill")
        return empty_figure("Error")
