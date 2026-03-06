"""Dashboard view callbacks — load, render widgets with grid, info modal, widget→query nav, cross-filter, AI chat."""

import pandas as pd
from dash import (
    Input, Output, State, callback, html, dcc, ctx, no_update, ALL,
)
import dash_bootstrap_components as dbc
import dash_draggable
from dash.exceptions import PreventUpdate
import plotly.express as px

from app.services.storage_service import StorageService
from app.services.label_service import get_label
from app.config import settings

CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107", "#9C27B0", "#FF5722"]

STATIC_DASHBOARD_ROUTES = {
    "visionamos", "contact-center", "bot-performance", "control-toques", "nuevo",
}


def _migrate_legacy_layout(layout_data):
    """Assign grid positions to legacy dashboards that don't have grid_* fields."""
    for i, w in enumerate(layout_data):
        if "grid_i" not in w:
            w["grid_i"] = f"widget-{i}"
            w["grid_x"] = (i % 2) * 6
            w["grid_y"] = (i // 2) * 4
            w["grid_w"] = w.get("width", 6)
            w["grid_h"] = 4
    return layout_data


def _render_widget(widget, index):
    """Render a single dashboard widget as an html.Div (for grid layout)."""
    widget_type = widget.get("type") or widget.get("chart_type", "table")
    title = widget.get("title", "Widget")
    data = widget.get("data", [])
    columns = widget.get("columns", [])
    query_id = widget.get("query_id")

    body_content = []

    if not data:
        body_content.append(
            html.Div([
                html.I(className="bi bi-inbox text-muted"),
                html.Small(" Sin datos", className="text-muted"),
            ], className="text-center py-3")
        )
    else:
        df = pd.DataFrame(data)

        if widget_type in ("bar", "line", "pie", "area", "histogram") and len(df.columns) >= 2:
            x_col, y_col = df.columns[0], df.columns[1]

            if df[y_col].dtype == "object":
                try:
                    df = df.copy()
                    df[y_col] = pd.to_numeric(
                        df[y_col].str.replace(",", "").str.replace("%", ""),
                        errors="coerce",
                    )
                except Exception:
                    pass

            label_map = {c: get_label(c) for c in df.columns}

            if widget_type == "line":
                fig = px.line(df, x=x_col, y=y_col, labels=label_map,
                              color_discrete_sequence=CHART_COLORS)
            elif widget_type == "pie":
                fig = px.pie(df, names=x_col, values=y_col, labels=label_map,
                             color_discrete_sequence=CHART_COLORS)
            elif widget_type == "area":
                fig = px.area(df, x=x_col, y=y_col, labels=label_map,
                              color_discrete_sequence=CHART_COLORS)
            elif widget_type == "histogram":
                fig = px.histogram(df, x=y_col, labels=label_map,
                                   color_discrete_sequence=CHART_COLORS)
            else:
                fig = px.bar(df, x=x_col, y=y_col, labels=label_map,
                             color_discrete_sequence=CHART_COLORS)

            # Calculate chart height from grid_h
            grid_h = widget.get("grid_h", 4)
            chart_height = max(grid_h * 80 - 100, 200)

            fig.update_layout(
                template="plotly_white",
                font_family="Inter, sans-serif",
                margin=dict(l=50, r=20, t=20, b=60),
                height=chart_height,
                showlegend=widget_type == "pie",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hoverlabel=dict(
                    bgcolor="#1A1A2E",
                    font_size=13,
                    font_family="Inter, sans-serif",
                ),
                xaxis=dict(automargin=True, tickangle=-45 if len(df) > 6 else 0),
                yaxis=dict(automargin=True),
            )
            body_content.append(
                dcc.Graph(
                    id={"type": "widget-chart", "index": index},
                    figure=fig,
                    config={"displayModeBar": False},
                )
            )

        if widget_type == "table" or widget.get("show_table"):
            from dash import dash_table
            display_columns = columns if columns else list(df.columns) if not df.empty else []
            body_content.append(
                dash_table.DataTable(
                    data=data[:50],
                    columns=[{"name": get_label(c), "id": c} for c in display_columns],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#F5F7FA",
                        "fontWeight": "600",
                        "fontSize": "12px",
                        "color": "#6E7191",
                    },
                    style_cell={
                        "fontSize": "12px",
                        "fontFamily": "Inter, sans-serif",
                        "padding": "6px 8px",
                    },
                )
            )

    widget_id = widget.get("grid_i", f"widget-{index}")

    return html.Div(
        dbc.Card([
            dbc.CardHeader([
                html.Span(title, className="fw-semibold small"),
                dbc.Button(
                    html.I(className="bi bi-info-circle"),
                    id={"type": "dv-widget-info", "index": index},
                    outline=True, color="primary", size="sm",
                    style={"padding": "2px 8px", "fontSize": "12px"},
                    title="Ver informacion y consulta asociada",
                ),
            ], className="py-2 px-3 bg-white d-flex justify-content-between align-items-center"),
            dbc.CardBody(body_content, className="p-2"),
        ], className="dashboard-widget h-100", style={
            "borderRadius": "16px", "border": "1px solid #F0F0F5",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.04)",
        }),
        id=widget_id,
        style={"height": "100%"},
    )


# --- Load dashboard ---

@callback(
    Output("dashboard-grid", "children"),
    Output("dv-title", "children"),
    Output("dv-subtitle", "children"),
    Input("url", "pathname"),
    State("tenant-context", "data"),
)
def load_dashboard(pathname, tenant):
    if not pathname or not pathname.startswith("/tableros/saved/"):
        raise PreventUpdate

    parts = pathname.strip("/").split("/")
    if len(parts) < 3 or parts[2] == "":
        raise PreventUpdate

    dashboard_id = parts[2]

    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.get_dashboard(dashboard_id)

    if not result:
        return (
            html.Div([
                html.I(className="bi bi-exclamation-triangle display-4 text-warning"),
                html.P("Tablero no encontrado.", className="text-muted mt-3"),
                dbc.Button("Volver a tableros", href="/tableros", color="primary", size="sm"),
            ], className="text-center py-5"),
            "Tablero no encontrado",
            "",
        )

    dashboard_name = result.get("name", f"Tablero #{dashboard_id}")
    description = result.get("description") or ""
    layout_data = result.get("layout") or []

    if not layout_data:
        return (
            html.Div([
                html.I(className="bi bi-grid-1x2 display-4 text-muted"),
                html.P("Este tablero no tiene widgets.",
                       className="text-muted mt-3"),
                dbc.Button(
                    [html.I(className="bi bi-pencil me-1"), "Editar tablero"],
                    href="/tableros/nuevo",
                    color="primary", size="sm",
                ),
            ], className="text-center py-5"),
            dashboard_name,
            description,
        )

    # Ensure all widgets have grid_* fields (backward compat)
    layout_data = _migrate_legacy_layout(layout_data)

    # Build grid children and layout
    children = []
    grid_items = []

    for i, w in enumerate(layout_data):
        widget_div = _render_widget(w, i)
        children.append(widget_div)

        widget_id = w.get("grid_i", f"widget-{i}")
        grid_items.append({
            "i": widget_id,
            "x": w.get("grid_x", (i % 2) * 6),
            "y": w.get("grid_y", (i // 2) * 4),
            "w": w.get("grid_w", w.get("width", 6)),
            "h": w.get("grid_h", 4),
            "static": True,  # View-only: no dragging
        })

    grid = dash_draggable.ResponsiveGridLayout(
        id="dashboard-view-grid",
        children=children,
        layouts={"lg": grid_items},
        gridCols={"lg": 12, "md": 10, "sm": 6, "xs": 4},
        rowHeight=80,
        isDraggable=False,
        isResizable=False,
        compactType="vertical",
        margin=[16, 16],
        style={"minHeight": "300px"},
    )

    return grid, dashboard_name, description


# --- Info modal ---

@callback(
    Output("dv-info-modal", "is_open"),
    Output("dv-info-modal-title", "children"),
    Output("dv-info-modal-body", "children"),
    Input({"type": "dv-widget-info", "index": ALL}, "n_clicks"),
    State("url", "pathname"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def show_widget_info(n_clicks_list, pathname, tenant):
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]

    # Load dashboard to get widget info
    if not pathname or not pathname.startswith("/tableros/saved/"):
        raise PreventUpdate

    parts = pathname.strip("/").split("/")
    if len(parts) < 3:
        raise PreventUpdate

    dashboard_id = parts[2]
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.get_dashboard(dashboard_id)

    if not result:
        raise PreventUpdate

    layout_data = result.get("layout") or []
    if idx >= len(layout_data):
        raise PreventUpdate

    w = layout_data[idx]
    title = w.get("title", "Widget")
    sql = w.get("sql", "")
    query_text = w.get("query_text", "")
    query_id = w.get("query_id")
    chart_type = w.get("type") or w.get("chart_type", "table")
    data = w.get("data", [])

    body = []

    if query_text:
        body.append(html.Div([
            html.Small("Pregunta original:", className="fw-bold text-muted"),
            html.P(query_text, className="mt-1", style={"fontSize": "14px"}),
        ], className="mb-3"))

    body.append(html.Div([
        dbc.Badge(f"Tipo: {chart_type.upper()}", color="primary", className="me-2"),
        dbc.Badge(f"{len(data)} filas", color="info", className="me-2"),
    ], className="mb-3"))

    if sql:
        body.append(html.Div([
            html.Small("SQL generado:", className="fw-bold text-muted"),
            html.Pre(sql, className="bg-light p-3 rounded small mt-1"),
        ], className="mb-3"))

    buttons = []
    if query_id:
        buttons.append(
            dbc.Button(
                [html.I(className="bi bi-box-arrow-up-right me-1"), "Ir a la consulta"],
                href=f"/consultas/nueva?rerun={query_id}",
                color="primary", size="sm",
                style={"borderRadius": "8px"},
                className="me-2",
            )
        )
    elif query_text:
        import urllib.parse
        encoded_q = urllib.parse.quote(query_text)
        buttons.append(
            dbc.Button(
                [html.I(className="bi bi-chat-dots me-1"), "Repetir consulta"],
                href=f"/consultas/nueva?q={encoded_q}",
                color="primary", size="sm",
                style={"borderRadius": "8px"},
                className="me-2",
            )
        )

    if buttons:
        body.append(html.Div(buttons, className="d-flex"))

    if not body:
        body.append(html.P("No hay informacion disponible.", className="text-muted"))

    return True, title, html.Div(body)


# --- Widget→Query navigation: click on chart redirects to query ---

@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("url", "search", allow_duplicate=True),
    Input({"type": "widget-chart", "index": ALL}, "clickData"),
    State("url", "pathname"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def widget_click_navigate(click_data_list, pathname, tenant):
    """When user clicks on a chart widget, navigate to the original query."""
    if not any(click_data_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "widget-chart":
        raise PreventUpdate

    idx = triggered["index"]

    # Load dashboard to find widget's query_id
    if not pathname or not pathname.startswith("/tableros/saved/"):
        raise PreventUpdate

    parts = pathname.strip("/").split("/")
    if len(parts) < 3:
        raise PreventUpdate

    dashboard_id = parts[2]
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.get_dashboard(dashboard_id)

    if not result:
        raise PreventUpdate

    layout_data = result.get("layout") or []
    if idx >= len(layout_data):
        raise PreventUpdate

    w = layout_data[idx]
    query_id = w.get("query_id")
    query_text = w.get("query_text", "")

    if query_id:
        return "/consultas/nueva", f"?rerun={query_id}"
    elif query_text:
        import urllib.parse
        return "/consultas/nueva", f"?q={urllib.parse.quote(query_text)}"

    raise PreventUpdate


# --- Cross-filter: click on chart stores filter ---

@callback(
    Output("dv-cross-filter", "data"),
    Output("dv-filter-badge", "children"),
    Input({"type": "widget-chart", "index": ALL}, "clickData"),
    Input("url", "pathname"),
    State("dv-cross-filter", "data"),
    prevent_initial_call=True,
)
def handle_cross_filter(click_data_list, pathname, current_filter):
    triggered = ctx.triggered_id

    # Clear filter on navigation
    if triggered == "url":
        return None, ""

    # Handle chart click
    if isinstance(triggered, dict) and triggered.get("type") == "widget-chart":
        for cd in click_data_list:
            if cd and cd.get("points"):
                point = cd["points"][0]
                label = point.get("x") or point.get("label", "")
                if label:
                    filter_data = {"column": "x", "value": str(label), "index": triggered["index"]}
                    badge = dbc.Alert([
                        html.I(className="bi bi-funnel me-2"),
                        f"Filtro activo: {label}",
                    ], color="info", className="mb-3 d-flex align-items-center py-2",
                       style={"fontSize": "13px"})
                    return filter_data, badge

    return no_update, no_update


# --- Toggle AI chat offcanvas ---

@callback(
    Output("ai-chat-offcanvas", "is_open"),
    Input("open-ai-chat", "n_clicks"),
    State("ai-chat-offcanvas", "is_open"),
    prevent_initial_call=True,
)
def toggle_ai_chat(n_clicks, is_open):
    return not is_open
