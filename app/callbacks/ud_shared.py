"""Shared helpers for unified dashboard tab callbacks."""

from datetime import date, timedelta

from dash import html, dcc
import dash_bootstrap_components as dbc

from app.services.chart_service import ChartService


def parse_range(date_range):
    """Parse a date range store value into (start, end) date objects."""
    if date_range:
        return (
            date.fromisoformat(str(date_range["start"])[:10]),
            date.fromisoformat(str(date_range["end"])[:10]),
        )
    today = date.today()
    return today - timedelta(days=29), today


def kpi_card(label, value, icon, color="primary", md=3):
    """Render a single KPI card with icon, label, and formatted value."""
    display_value = f"{value:,}" if isinstance(value, int) else str(value)
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {icon} me-2 text-{color}"),
                    html.Span(label, className="kpi-label"),
                ]),
                html.Div(
                    html.Span(display_value, className="kpi-value"),
                    className="mt-1",
                ),
            ]),
        ], className="kpi-card"),
        md=md, sm=6, xs=12,
    )


def kpi_card_with_delta(label, value, delta_pct, icon, color="primary", md=3):
    """KPI card with a delta percentage indicator (positive=green, negative=red)."""
    display_value = f"{value:,}" if isinstance(value, int) else str(value)
    if delta_pct is None or delta_pct == 0:
        delta_el = html.Span("—", style={"fontSize": "12px", "color": "#A0A3BD"})
    else:
        arrow = "▲" if delta_pct > 0 else "▼"
        delta_color = "#76C043" if delta_pct > 0 else "#EF4444"
        delta_el = html.Span(
            f"{arrow} {abs(delta_pct):.1f}%",
            style={"fontSize": "12px", "fontWeight": "500", "color": delta_color},
        )
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {icon} me-2 text-{color}"),
                    html.Span(label, className="kpi-label"),
                ]),
                html.Div([
                    html.Span(display_value, className="kpi-value me-2"),
                    delta_el,
                ], className="mt-1 d-flex align-items-baseline"),
            ]),
        ], className="kpi-card"),
        md=md, sm=6, xs=12,
    )


def no_data_alert(channel_name):
    """Alert banner shown when a channel has no data available."""
    return dbc.Alert([
        html.I(className="bi bi-info-circle-fill me-2"),
        html.Strong(f"Canal {channel_name} sin datos. "),
        "Este canal no esta habilitado para la cuenta actual. ",
        "Los datos se mostraran automaticamente cuando el canal sea activado.",
    ], color="info", className="mb-3")


def empty_figure(title=""):
    """Return an empty Plotly figure with a 'no data' annotation."""
    return ChartService()._create_empty_chart(title)
