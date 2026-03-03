"""Unified Dashboard — General (overview) tab callbacks."""

import logging

import plotly.graph_objects as go
from dash import Input, Output, callback

from app.callbacks.ud_shared import parse_range, kpi_card, empty_figure
from app.services.general_dashboard_service import GeneralDashboardService
from app.services.chart_service import ChartService

log = logging.getLogger(__name__)

FUNNEL_COLORS = ["#1E88E5", "#76C043", "#42A5F5", "#FFC107"]


@callback(
    Output("ud-gen-kpi-row", "children"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_gen_kpis(date_range, tenant):
    try:
        svc = GeneralDashboardService()
        start, end = parse_range(date_range)
        kpis = svc.get_overview_kpis(
            tenant_filter=tenant, start_date=start, end_date=end
        )
    except Exception:
        log.exception("Error loading General KPIs")
        kpis = {
            "total_events": 0, "total_sent": 0, "total_delivered": 0,
            "delivery_rate": 0, "total_read_opened": 0, "read_rate": 0,
            "total_clicked": 0, "ctr": 0,
        }
    return [
        kpi_card("Total Eventos", kpis["total_events"], "bi-activity", md=3),
        kpi_card("Enviados", kpis["total_sent"], "bi-send", "primary", md=3),
        kpi_card("Entregados", kpis["total_delivered"], "bi-check2-circle", "success", md=3),
        kpi_card("Tasa Entrega", f"{kpis['delivery_rate']}%", "bi-percent", "info", md=3),
        kpi_card("Leidos/Abiertos", kpis["total_read_opened"], "bi-eye", "primary", md=3),
        kpi_card("Tasa Lectura", f"{kpis['read_rate']}%", "bi-book", "info", md=3),
        kpi_card("Clicks", kpis["total_clicked"], "bi-cursor", "warning", md=3),
        kpi_card("CTR", f"{kpis['ctr']}%", "bi-graph-up-arrow", "success", md=3),
    ]


@callback(
    Output("ud-gen-funnel-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_gen_funnel(date_range, tenant):
    try:
        svc = GeneralDashboardService()
        start, end = parse_range(date_range)
        df = svc.get_delivery_funnel(
            tenant_filter=tenant, start_date=start, end_date=end
        )
        if df.empty:
            return empty_figure("Sin datos")

        fig = go.Figure(go.Bar(
            y=df["etapa"],
            x=df["cantidad"],
            orientation="h",
            marker_color=FUNNEL_COLORS,
            text=df["cantidad"].apply(lambda v: f"{v:,}"),
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter, sans-serif", "size": 12, "color": "#6E7191"},
            margin={"l": 100, "r": 20, "t": 10, "b": 30},
            xaxis={"gridcolor": "#E4E4E7", "linecolor": "#E4E4E7"},
            yaxis={"autorange": "reversed"},
            hoverlabel={"bgcolor": "#1A1A2E", "font_size": 13},
        )
        return fig
    except Exception:
        log.exception("Error loading General funnel")
        return empty_figure("Sin datos")


@callback(
    Output("ud-gen-trend-chart", "figure"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_gen_trend(date_range, tenant):
    try:
        svc = GeneralDashboardService()
        charts = ChartService()
        start, end = parse_range(date_range)
        df = svc.get_combined_daily_trend(
            tenant_filter=tenant, start_date=start, end_date=end
        )
        if df.empty:
            return empty_figure("Tendencia Multicanal")

        cols = [c for c in df.columns if c != "date"]
        return charts.create_multi_line_chart(
            df, "", "date", cols,
            {c: c for c in cols},
        )
    except Exception:
        log.exception("Error loading General trend")
        return empty_figure("Tendencia Multicanal")


@callback(
    Output("ud-gen-channel-table", "data"),
    Output("ud-gen-channel-table", "columns"),
    Input("ud-date-store", "data"),
    Input("tenant-context", "data"),
)
def load_ud_gen_channel_table(date_range, tenant):
    try:
        svc = GeneralDashboardService()
        start, end = parse_range(date_range)
        df = svc.get_channel_summary_table(
            tenant_filter=tenant, start_date=start, end_date=end
        )
        if df.empty:
            return [], []
        col_map = {
            "channel_name": "Canal",
            "enviados": "Enviados",
            "entregados": "Entregados",
            "tasa_entrega": "% Entrega",
            "leidos": "Leidos",
            "tasa_lectura": "% Lectura",
            "clicks": "Clicks",
            "ctr": "CTR %",
            "errores": "Errores",
        }
        columns = [
            {"name": col_map.get(c, c), "id": c}
            for c in df.columns if c in col_map
        ]
        return df.to_dict("records"), columns
    except Exception:
        log.exception("Error loading General channel table")
        return [], []
