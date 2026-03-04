"""Dashboard builder callbacks — add/remove/resize widgets, save, edit, AI assistant."""

import json
import logging
import pandas as pd
from dash import (
    Input, Output, State, callback, html, dcc, ctx, no_update, ALL,
)
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px

from app.services.storage_service import StorageService
from app.services.label_service import get_label
from app.config import settings

logger = logging.getLogger(__name__)

CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107", "#9C27B0", "#FF5722"]


def _render_widget_chart(data, chart_type, height=300):
    """Render a chart from query result data."""
    if not data:
        return html.Div(
            html.Small("Sin datos", className="text-muted"),
            className="text-center py-3",
        )

    df = pd.DataFrame(data)
    if df.empty or len(df.columns) < 2:
        return html.Div(
            html.Small("Datos insuficientes para graficar", className="text-muted"),
            className="text-center py-3",
        )

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

    if chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col, labels=label_map, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "pie":
        fig = px.pie(df, names=x_col, values=y_col, labels=label_map, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "area":
        fig = px.area(df, x=x_col, y=y_col, labels=label_map, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "histogram":
        fig = px.histogram(df, x=y_col, labels=label_map, color_discrete_sequence=CHART_COLORS)
    else:
        fig = px.bar(df, x=x_col, y=y_col, labels=label_map, color_discrete_sequence=CHART_COLORS)

    fig.update_layout(
        template="plotly_white",
        font_family="Inter, sans-serif",
        margin=dict(l=50, r=20, t=20, b=60),
        height=height,
        showlegend=chart_type == "pie",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#1A1A2E", font_size=13, font_family="Inter"),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
    )

    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _render_canvas(widgets):
    """Render the full widget canvas from the widgets list."""
    if not widgets:
        return html.Div([
            html.I(className="bi bi-grid-1x2 display-4 text-muted"),
            html.P("Agrega consultas desde el panel lateral para crear widgets.",
                   className="text-muted mt-3"),
        ], className="text-center py-5", id="builder-empty-state")

    cols = []
    for i, w in enumerate(widgets):
        width = max(w.get("width", 6), 4)  # Minimum 4 columns
        chart_type = w.get("type") or w.get("chart_type", "bar")
        title = w.get("title", "Widget")
        data = w.get("data", [])

        card = dbc.Card([
            dbc.CardHeader([
                html.Span(title, className="fw-semibold small"),
                html.Div([
                    dbc.Button(
                        html.I(className="bi bi-info-circle"),
                        id={"type": "builder-widget-info", "index": i},
                        outline=True, color="secondary", size="sm",
                        className="me-1",
                        style={"padding": "1px 5px", "fontSize": "11px"},
                        title="Ver SQL",
                    ),
                    dbc.Button(
                        html.I(className="bi bi-arrows-angle-expand"),
                        id={"type": "builder-widget-resize", "index": i},
                        outline=True, color="secondary", size="sm",
                        className="me-1",
                        style={"padding": "1px 5px", "fontSize": "11px"},
                        title=f"Ancho actual: {width}/12",
                    ),
                    dbc.Button(
                        html.I(className="bi bi-x-lg"),
                        id={"type": "builder-widget-remove", "index": i},
                        outline=True, color="danger", size="sm",
                        style={"padding": "1px 5px", "fontSize": "11px"},
                        title="Eliminar",
                    ),
                ], className="d-flex"),
            ], className="py-2 px-3 bg-white d-flex justify-content-between align-items-center"),
            dbc.CardBody(
                _render_widget_chart(data, chart_type),
                className="p-2",
            ),
        ], className="dashboard-widget h-100", style={
            "borderRadius": "16px", "border": "1px solid #F0F0F5",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.04)",
        })

        cols.append(dbc.Col(card, md=width, className="mb-3"))

    return dbc.Row(cols, className="g-3")


# --- 1. Load available queries for panel ---

@callback(
    Output("builder-query-list", "children"),
    Input("tenant-context", "data"),
)
def load_available_queries(tenant):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.list_queries(limit=30)

    if not result["queries"]:
        return html.Div([
            html.Small("No hay consultas guardadas.", className="text-muted"),
            dbc.Button(
                [html.I(className="bi bi-plus-lg me-1"), "Crear Consulta"],
                href="/consultas/nueva", color="primary", size="sm", className="mt-2",
            ),
        ], className="text-center py-3")

    items = []
    for q in result["queries"]:
        viz = q.get("visualizations") or []
        chart_type = viz[0].get("type", "table") if viz else "table"
        row_count = q.get("result_row_count", 0)

        items.append(
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Small(q["name"][:50], className="fw-semibold",
                                   style={"fontSize": "12px", "color": "#1A1A2E"}),
                    ]),
                    html.Div([
                        dbc.Badge(chart_type.upper(), color="primary",
                                  style={"fontSize": "9px"}, className="me-1"),
                        html.Small(f"{row_count} filas", className="text-muted",
                                   style={"fontSize": "10px"}),
                    ], className="mt-1"),
                    dbc.Button(
                        [html.I(className="bi bi-plus me-1"), "Agregar"],
                        id={"type": "builder-add-query", "index": q["id"]},
                        outline=True, color="primary", size="sm",
                        className="mt-2 w-100",
                        style={"borderRadius": "6px", "fontSize": "11px"},
                    ),
                ], className="py-2 px-2"),
            ], className="mb-2", style={
                "borderRadius": "10px", "border": "1px solid #F0F0F5",
                "cursor": "pointer",
            })
        )

    return html.Div(items)


# --- 2. Add widget to canvas ---

@callback(
    Output("builder-widgets", "data", allow_duplicate=True),
    Input({"type": "builder-add-query", "index": ALL}, "n_clicks"),
    State("builder-widgets", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def add_widget(n_clicks_list, widgets, tenant):
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    query_id = triggered["index"]
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    query = svc.get_query(query_id)
    if not query:
        raise PreventUpdate

    viz = query.get("visualizations") or []
    chart_type = viz[0].get("type", "bar") if viz else "bar"

    widget = {
        "query_id": query_id,
        "title": query["name"][:60],
        "type": chart_type,
        "chart_type": chart_type,
        "width": 6,
        "data": query.get("result_data") or [],
        "columns": [c["name"] for c in (query.get("result_columns") or [])],
        "sql": query.get("generated_sql") or "",
        "query_text": query.get("query_text") or "",
    }

    widgets = widgets or []
    widgets.append(widget)
    return widgets


# --- 3. Remove widget ---

@callback(
    Output("builder-widgets", "data", allow_duplicate=True),
    Input({"type": "builder-widget-remove", "index": ALL}, "n_clicks"),
    State("builder-widgets", "data"),
    prevent_initial_call=True,
)
def remove_widget(n_clicks_list, widgets):
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]
    widgets = widgets or []
    if 0 <= idx < len(widgets):
        widgets.pop(idx)

    return widgets


# --- 4. Resize widget (cycle 4 → 6 → 12 → 4) ---

@callback(
    Output("builder-widgets", "data", allow_duplicate=True),
    Input({"type": "builder-widget-resize", "index": ALL}, "n_clicks"),
    State("builder-widgets", "data"),
    prevent_initial_call=True,
)
def resize_widget(n_clicks_list, widgets):
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]
    widgets = widgets or []
    if 0 <= idx < len(widgets):
        current = widgets[idx].get("width", 6)
        cycle = {4: 6, 6: 12, 12: 4}
        widgets[idx]["width"] = cycle.get(current, 6)

    return widgets


# --- 5. Render canvas when widgets change ---

@callback(
    Output("builder-canvas", "children"),
    Input("builder-widgets", "data"),
)
def render_canvas(widgets):
    return _render_canvas(widgets or [])


# --- 6. Save / Update dashboard ---

@callback(
    Output("builder-save-feedback", "children"),
    Output("builder-dashboard-id", "data"),
    Input("builder-save-btn", "n_clicks"),
    State("builder-name", "value"),
    State("builder-description", "value"),
    State("builder-widgets", "data"),
    State("builder-dashboard-id", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def save_dashboard(n_clicks, name, description, widgets, existing_id, tenant):
    if not name or not name.strip():
        return dbc.Alert(
            "Por favor ingresa un nombre para el tablero.",
            color="warning", duration=3000, dismissable=True,
        ), no_update

    if not widgets:
        return dbc.Alert(
            "Agrega al menos un widget antes de guardar.",
            color="warning", duration=3000, dismissable=True,
        ), no_update

    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)

    # Update existing dashboard if editing
    if existing_id:
        result = svc.update_dashboard_layout(existing_id, widgets)
        if result.get("success"):
            return dbc.Alert([
                html.I(className="bi bi-check-circle me-2"),
                f"Tablero \"{name}\" actualizado exitosamente. ",
                html.A("Ver tablero", href=f"/tableros/saved/{existing_id}",
                       className="alert-link"),
            ], color="success", duration=5000, dismissable=True), existing_id

        return dbc.Alert(
            "Error actualizando el tablero. Intenta de nuevo.",
            color="danger", duration=3000, dismissable=True,
        ), no_update

    # Create new dashboard
    result = svc.save_dashboard(
        name=name.strip(),
        description=description.strip() if description else None,
        layout=widgets,
    )

    if result.get("success"):
        return dbc.Alert([
            html.I(className="bi bi-check-circle me-2"),
            f"Tablero \"{name}\" guardado exitosamente. ",
            html.A("Ver tablero", href=f"/tableros/saved/{result['id']}",
                   className="alert-link"),
        ], color="success", duration=5000, dismissable=True), result["id"]

    return dbc.Alert(
        "Error guardando el tablero. Intenta de nuevo.",
        color="danger", duration=3000, dismissable=True,
    ), no_update


# --- 7. Load from URL: ?query_id=<id> or ?edit=<dashboard_id> ---

@callback(
    Output("builder-widgets", "data", allow_duplicate=True),
    Output("builder-name", "value"),
    Output("builder-description", "value"),
    Output("builder-dashboard-id", "data", allow_duplicate=True),
    Input("builder-url", "search"),
    State("builder-widgets", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def load_from_url(search, widgets, tenant):
    if not search:
        raise PreventUpdate

    import urllib.parse
    params = urllib.parse.parse_qs(search.lstrip("?"))
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)

    # --- Edit existing dashboard ---
    edit_id = params.get("edit", [None])[0]
    if edit_id:
        dashboard = svc.get_dashboard(int(edit_id))
        if not dashboard:
            raise PreventUpdate

        loaded_widgets = dashboard.get("layout") or []
        name = dashboard.get("name", "")
        description = dashboard.get("description") or ""
        return loaded_widgets, name, description, int(edit_id)

    # --- Pre-load a single query ---
    query_id = params.get("query_id", [None])[0]
    if query_id:
        query = svc.get_query(int(query_id))
        if not query:
            raise PreventUpdate

        viz = query.get("visualizations") or []
        chart_type = viz[0].get("type", "bar") if viz else "bar"

        widget = {
            "query_id": int(query_id),
            "title": query["name"][:60],
            "type": chart_type,
            "chart_type": chart_type,
            "width": 6,
            "data": query.get("result_data") or [],
            "columns": [c["name"] for c in (query.get("result_columns") or [])],
            "sql": query.get("generated_sql") or "",
            "query_text": query.get("query_text") or "",
        }

        widgets = widgets or []
        if not any(w.get("query_id") == int(query_id) for w in widgets):
            widgets.append(widget)

        return widgets, no_update, no_update, no_update

    raise PreventUpdate


# --- 8. Show widget SQL info ---

@callback(
    Output("builder-sql-modal", "is_open"),
    Output("builder-sql-modal-title", "children"),
    Output("builder-sql-modal-body", "children"),
    Input({"type": "builder-widget-info", "index": ALL}, "n_clicks"),
    State("builder-widgets", "data"),
    prevent_initial_call=True,
)
def show_widget_sql(n_clicks_list, widgets):
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]
    widgets = widgets or []
    if idx >= len(widgets):
        raise PreventUpdate

    w = widgets[idx]
    title = w.get("title", "Widget")
    sql = w.get("sql", "")
    query_text = w.get("query_text", "")
    query_id = w.get("query_id")

    body = []
    if query_text:
        body.append(html.Div([
            html.Small("Pregunta original:", className="fw-bold text-muted"),
            html.P(query_text, className="mt-1", style={"fontSize": "14px"}),
        ], className="mb-3"))

    if sql:
        body.append(html.Div([
            html.Small("SQL generado:", className="fw-bold text-muted"),
            html.Pre(sql, className="bg-light p-3 rounded small mt-1"),
        ], className="mb-3"))

    if query_id:
        body.append(
            dbc.Button(
                [html.I(className="bi bi-box-arrow-up-right me-1"), "Ir a la consulta"],
                href=f"/consultas/nueva?rerun={query_id}",
                color="primary", size="sm",
                style={"borderRadius": "8px"},
            )
        )

    if not body:
        body.append(html.P("No hay informacion disponible.", className="text-muted"))

    return True, title, html.Div(body)


# --- 9. Toggle AI offcanvas ---

@callback(
    Output("builder-ai-offcanvas", "is_open"),
    Input("builder-ai-fab", "n_clicks"),
    State("builder-ai-offcanvas", "is_open"),
    prevent_initial_call=True,
)
def toggle_builder_ai(n_clicks, is_open):
    return not is_open


# --- 10. AI chat in builder — generates clickable NL question chips ---

@callback(
    Output("builder-ai-chat", "children"),
    Output("builder-ai-input", "value"),
    Output("builder-ai-suggestions", "data"),
    Input("builder-ai-send", "n_clicks"),
    State("builder-ai-input", "value"),
    State("builder-widgets", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def builder_ai_chat(n_clicks, message, widgets, tenant):
    if not message or not message.strip():
        raise PreventUpdate

    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    available = svc.list_queries(limit=20)
    available_queries = available.get("queries", [])

    elements = []
    suggestion_texts = []

    # User message bubble
    elements.append(html.Div([
        html.Small(message, className="fw-semibold"),
    ], className="p-2 mb-2 text-end", style={
        "backgroundColor": "#1E88E5", "color": "white", "borderRadius": "12px",
    }))

    # Collect NL questions from AI or fallback
    nl_questions = []
    add_existing_ids = []  # query_ids from saved queries to suggest adding

    try:
        from app.services.dashboard_ai_service import DashboardAIService
        ai_svc = DashboardAIService()
        result = ai_svc.suggest_dashboard(message, available_queries, widgets or [])

        response_text = result.get("response", "")
        suggestions = result.get("suggestions", [])

        elements.append(html.Div([
            html.I(className="bi bi-stars me-2", style={"color": "#1E88E5"}),
            html.Small(response_text),
        ], className="p-3 mb-2", style={
            "backgroundColor": "#F5F7FA", "borderRadius": "12px",
        }))

        # Separate: saved queries to add directly vs NL questions to execute
        for sug in suggestions:
            q_id = sug.get("query_id")
            if q_id:
                add_existing_ids.append(q_id)
            sug_title = sug.get("title", "")
            if sug_title and not q_id:
                nl_questions.append(sug_title)

        # Also generate NL suggestions based on user description
        if len(nl_questions) < 3:
            fallback_qs = _generate_nl_suggestions(message)
            for q in fallback_qs:
                if q not in nl_questions and len(nl_questions) < 5:
                    nl_questions.append(q)

    except Exception as e:
        logger.warning("Builder AI failed: %s", e)
        nl_questions = _generate_nl_suggestions(message)

        elements.append(html.Div([
            html.I(className="bi bi-stars me-2", style={"color": "#1E88E5"}),
            html.Small(
                "Te sugiero estas consultas para tu tablero. "
                "Haz clic en cualquiera para ejecutarla y agregarla como widget:"
            ),
        ], className="p-3 mb-2", style={
            "backgroundColor": "#F5F7FA", "borderRadius": "12px",
        }))

    # Render existing saved queries as "Agregar" buttons
    for q_id in add_existing_ids:
        q = next((qq for qq in available_queries if qq["id"] == q_id), None)
        if q:
            elements.append(html.Div([
                html.Small(q["name"][:50], className="fw-semibold d-block"),
                dbc.Button(
                    [html.I(className="bi bi-plus-circle me-1"), "Agregar al tablero"],
                    id={"type": "builder-add-query", "index": q_id},
                    color="primary", size="sm", outline=True,
                    className="mt-1",
                    style={"borderRadius": "6px", "fontSize": "11px"},
                ),
            ], className="p-2 mb-1", style={
                "backgroundColor": "#FAFBFC", "borderRadius": "8px",
                "border": "1px solid #F0F0F5",
            }))

    # Render NL questions as clickable execution chips
    suggestion_texts = nl_questions[:5]
    if suggestion_texts:
        elements.append(html.Small(
            "Haz clic para ejecutar y agregar al tablero:",
            className="text-muted d-block mb-2 mt-2",
            style={"fontSize": "11px"},
        ))
    for idx, q_text in enumerate(suggestion_texts):
        elements.append(
            dbc.Button(
                [html.I(className="bi bi-play-circle me-2"), q_text],
                id={"type": "builder-ai-chip", "index": idx},
                color="light", size="sm",
                className="text-start w-100 mb-1",
                style={
                    "borderRadius": "8px", "fontSize": "12px",
                    "border": "1px solid #E4E4E7", "color": "#1A1A2E",
                },
            )
        )

    return elements, "", suggestion_texts


# --- 11. Execute AI chip: run NL question, create widget, add to canvas ---

@callback(
    Output("builder-widgets", "data", allow_duplicate=True),
    Output("builder-ai-chat", "children", allow_duplicate=True),
    Input({"type": "builder-ai-chip", "index": ALL}, "n_clicks"),
    State("builder-ai-suggestions", "data"),
    State("builder-widgets", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def execute_ai_chip(n_clicks_list, suggestion_texts, widgets, tenant):
    """Execute an AI-suggested NL question and add the result as a widget."""
    if not any(n_clicks_list):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]
    suggestion_texts = suggestion_texts or []
    if idx >= len(suggestion_texts):
        raise PreventUpdate

    question = suggestion_texts[idx]

    # Show loading state
    loading_msg = html.Div([
        dbc.Spinner(size="sm", color="primary", className="me-2"),
        html.Small(f"Ejecutando: {question}...", className="fw-semibold"),
    ], className="p-3 mb-2", style={
        "backgroundColor": "#FFF8E1", "borderRadius": "12px",
    })

    # Execute via AIAgent
    try:
        from app.services.data_service import DataService
        from app.services.ai_agent import AIAgent

        data_svc = DataService()
        agent = AIAgent(data_svc)

        result = agent.process_query(
            user_question=question,
            tenant_filter=tenant or settings.DEFAULT_TENANT,
        )

        df = result.get("data")
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            chart_type = result.get("chart_type") or "bar"
            query_details = result.get("query_details") or {}

            widget = {
                "title": question[:60],
                "type": chart_type,
                "chart_type": chart_type,
                "width": 6,
                "data": df.to_dict("records"),
                "columns": list(df.columns),
                "sql": query_details.get("sql", ""),
                "query_text": question,
            }

            widgets = widgets or []
            widgets.append(widget)

            success_msg = html.Div([
                html.I(className="bi bi-check-circle me-2", style={"color": "#76C043"}),
                html.Small([
                    html.Span("Agregado: ", className="fw-semibold"),
                    question[:50],
                    html.Span(f" ({len(df)} filas, {chart_type})",
                              className="text-muted"),
                ]),
            ], className="p-2 mb-1", style={
                "backgroundColor": "#E8F5E9", "borderRadius": "8px",
            })

            return widgets, success_msg
        else:
            explanation = result.get("response", "Sin resultados")
            error_msg = html.Div([
                html.I(className="bi bi-info-circle me-2", style={"color": "#FFC107"}),
                html.Small(f"Sin datos para: {question}. {explanation[:100]}"),
            ], className="p-2 mb-1", style={
                "backgroundColor": "#FFF8E1", "borderRadius": "8px",
            })
            return no_update, error_msg

    except Exception as e:
        logger.error("AI chip execution failed: %s", e)
        error_msg = html.Div([
            html.I(className="bi bi-exclamation-triangle me-2", style={"color": "#EF4444"}),
            html.Small(f"Error ejecutando consulta: {str(e)[:100]}"),
        ], className="p-2 mb-1", style={
            "backgroundColor": "#FFEBEE", "borderRadius": "8px",
        })
        return no_update, error_msg


def _generate_nl_suggestions(user_description: str) -> list:
    """Generate relevant NL question suggestions based on user's description."""
    desc_lower = user_description.lower()
    suggestions = []

    if any(kw in desc_lower for kw in ["tendencia", "tiempo", "evolucion", "diario"]):
        suggestions.append("¿Cual es la tendencia de mensajes por dia?")
    if any(kw in desc_lower for kw in ["canal", "whatsapp", "sms", "email"]):
        suggestions.append("¿Que canal tiene mayor volumen de mensajes?")
    if any(kw in desc_lower for kw in ["agente", "rendimiento", "equipo"]):
        suggestions.append("¿Cual es el rendimiento de los agentes?")
    if any(kw in desc_lower for kw in ["contacto", "cliente", "usuario"]):
        suggestions.append("¿Cuales son los contactos mas activos?")
    if any(kw in desc_lower for kw in ["hora", "horario", "pico"]):
        suggestions.append("¿Cual es el horario pico de mensajes?")
    if any(kw in desc_lower for kw in ["fallback", "bot", "chatbot"]):
        suggestions.append("¿Cual es la tasa de fallback del bot?")
    if any(kw in desc_lower for kw in ["semana", "dia de la semana"]):
        suggestions.append("¿Que dia de la semana tiene mas mensajes?")
    if any(kw in desc_lower for kw in ["resumen", "general", "kpi"]):
        suggestions.append("Dame un resumen general de los datos")

    defaults = [
        "Dame un resumen general de los datos",
        "¿Cual es la tendencia de mensajes por dia?",
        "¿Cuales son los contactos mas activos?",
        "¿Cual es el rendimiento de los agentes?",
        "¿Cual es la tasa de fallback del bot?",
    ]
    for d in defaults:
        if d not in suggestions and len(suggestions) < 5:
            suggestions.append(d)

    return suggestions[:5]
