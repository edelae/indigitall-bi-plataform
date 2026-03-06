"""
Query page callbacks — AI chat interaction, chart type selector, Redash-style source panel,
conversation persistence, results rendering, save/export.
"""

import pandas as pd
from dash import (
    Input, Output, State, callback, html, dcc, no_update, ctx,
    ALL,
)
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px

from app.services.data_service import DataService
from app.services.ai_agent import AIAgent
from app.services.storage_service import StorageService
from app.services.schema_service import SchemaService
from app.services.label_service import get_label
from app.config import settings

# Chart color sequence from design system
CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107", "#9C27B0", "#FF5722"]

# Chart type definitions (must match query.py CHART_TYPES)
CHART_TYPE_LIST = ["bar", "line", "pie", "area", "histogram", "table"]

# Suggestion chips (must match query.py SUGGESTIONS order and content)
SUGGESTIONS = [
    "Dame un resumen general de los datos",
    "Cual es la tasa de fallback?",
    "Mensajes por hora del dia",
    "Top 10 contactos mas activos",
    "Rendimiento de agentes",
    "Comparacion entre entidades",
    "Distribucion de intenciones",
    "Mensajes por dia de la semana",
    "Tendencia de mensajes en el tiempo",
]

# Singleton-ish agent (created once per worker process)
_data_service = DataService()
_agent = AIAgent(_data_service)


def _render_user_message(text):
    return html.Div([
        html.Div(text, className="chat-message user-msg"),
    ], className="mb-3")


def _render_assistant_message(text):
    return html.Div([
        html.Div([
            html.I(className="bi bi-robot me-2"),
            dcc.Markdown(text, className="d-inline"),
        ], className="chat-message assistant-msg"),
    ], className="mb-3")


def _auto_chart(df, chart_type=None):
    """Generate a chart from a DataFrame, respecting AI-suggested chart_type."""
    if df.empty or len(df.columns) < 2:
        return None

    x_col = df.columns[0]
    y_col = df.columns[1]

    # Try to make y numeric for charting
    if df[y_col].dtype == "object":
        try:
            df = df.copy()
            df[y_col] = pd.to_numeric(df[y_col].str.replace(",", "").str.replace("%", ""), errors="coerce")
        except Exception:
            return None
        if df[y_col].isna().all():
            return None

    label_map = {c: get_label(c) for c in df.columns}

    # Determine chart type: explicit > AI-suggested > auto-detect
    if not chart_type:
        x_lower = x_col.lower()
        if any(kw in x_lower for kw in ["date", "fecha", "time", "dia", "mes", "month"]):
            chart_type = "line"
        elif len(df) <= 8 and len(df.columns) == 2:
            chart_type = "pie"
        else:
            chart_type = "bar"

    if chart_type == "table":
        return None

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
        margin=dict(l=40, r=20, t=30, b=50),
        height=350,
        showlegend=chart_type == "pie",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#1A1A2E",
        hoverlabel=dict(bgcolor="#1A1A2E", font_size=13, font_family="Inter"),
        xaxis=dict(title=get_label(x_col), automargin=True,
                   tickangle=-45 if len(df) > 6 else 0),
        yaxis=dict(title=get_label(y_col), automargin=True),
    )
    return fig


def _build_results_panel(df, chart_type, query_details):
    """Build the main results panel with chart + mini table side by side."""
    results = []

    if not df.empty:
        fig = _auto_chart(df, chart_type)

        if fig:
            # Chart (col-8) + mini table preview (col-4) side by side
            from dash import dash_table
            mini_data = df.head(5).to_dict("records")
            results.append(
                dbc.Row([
                    dbc.Col(
                        dcc.Graph(figure=fig, config={"displayModeBar": False}, className="mb-2"),
                        md=8,
                    ),
                    dbc.Col(
                        dash_table.DataTable(
                            data=mini_data,
                            columns=[{"name": get_label(c), "id": c} for c in df.columns],
                            page_size=5,
                            style_table={"overflowX": "auto", "fontSize": "11px"},
                            style_header={
                                "backgroundColor": "#F5F7FA", "fontWeight": "600",
                                "fontSize": "11px", "color": "#6E7191",
                            },
                            style_cell={
                                "fontSize": "11px", "fontFamily": "Inter, sans-serif",
                                "padding": "4px 6px",
                            },
                        ),
                        md=4,
                    ),
                ], className="g-2 mb-3")
            )
        else:
            # Table-only view (chart_type == "table" or no chart possible)
            from dash import dash_table
            results.append(
                dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": get_label(c), "id": c} for c in df.columns],
                    page_size=15,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#F5F7FA", "fontWeight": "600",
                        "fontSize": "13px", "color": "#6E7191", "textTransform": "uppercase",
                    },
                    style_cell={
                        "fontSize": "13px", "fontFamily": "Inter, sans-serif",
                        "padding": "8px 12px",
                    },
                    style_data_conditional=[{
                        "if": {"row_index": "odd"}, "backgroundColor": "#FAFBFC",
                    }],
                )
            )

        results.append(html.Small(f"{len(df)} filas", className="text-muted mt-2 d-block"))

        # Show SQL details if it was an ad-hoc query
        if query_details and query_details.get("sql"):
            results.append(
                dbc.Accordion([
                    dbc.AccordionItem(
                        html.Pre(query_details["sql"], className="bg-light p-3 rounded small"),
                        title="Ver SQL generado",
                    ),
                ], start_collapsed=True, className="mt-2")
            )
    else:
        results.append(html.Div([
            html.I(className="bi bi-info-circle display-4 text-muted"),
            html.P("Sin datos para mostrar.", className="text-muted mt-3"),
        ], className="text-center py-5"))

    return results


def _build_source_tab(df, ai_function, query_details, tenant=None):
    """Build the Redash-style 'Fuente de Datos' tab with sidebar + SQL + results."""
    from dash import dash_table

    elements = []

    # 3-panel layout: sidebar (col-3) + right panel (col-9)
    try:
        schema_svc = SchemaService()
        tables_with_cols = schema_svc.list_all_tables_with_columns()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("SchemaService failed in source tab: %s", e)
        tables_with_cols = []

    # Build sidebar with collapsible table tree
    sidebar_items = []
    for table_info in tables_with_cols:
        tname = table_info["table_name"]
        row_count = table_info.get("row_count", 0)
        cols = table_info.get("columns", [])

        col_list = []
        for col in cols:
            dtype_badge = dbc.Badge(
                col["data_type"][:15], color="light", text_color="dark",
                className="ms-auto", style={"fontSize": "9px"},
            )
            col_list.append(
                html.Div([
                    html.Small(col["column_name"], style={"fontSize": "12px", "color": "#1A1A2E"}),
                    dtype_badge,
                ], className="d-flex align-items-center justify-content-between py-1 px-2",
                   style={"borderBottom": "1px solid #F5F7FA"})
            )

        sidebar_items.append(
            dbc.AccordionItem(
                html.Div(col_list) if col_list else html.Small("Sin columnas", className="text-muted"),
                title=html.Span([
                    tname,
                    dbc.Badge(f"{row_count}", color="info", className="ms-2", style={"fontSize": "9px"}),
                ]),
            )
        )

    sidebar = html.Div([
        dbc.Input(
            id="source-table-search",
            placeholder="Buscar tabla...",
            size="sm", className="mb-2",
            style={"borderRadius": "8px", "fontSize": "12px"},
        ),
        dbc.Accordion(
            sidebar_items,
            start_collapsed=True,
            className="source-table-tree",
        ) if sidebar_items else html.Small("No hay tablas disponibles.", className="text-muted"),
    ], className="source-sidebar")

    # Right panel: SQL + Results
    sql_text = ""
    if query_details and query_details.get("sql"):
        sql_text = query_details["sql"]
    elif ai_function:
        sql_text = f"-- Funcion pre-construida: {ai_function}"

    sql_panel = html.Div([
        html.Div([
            html.Small("SQL Ejecutado", className="fw-bold", style={"color": "#A0A3BD", "fontSize": "11px"}),
        ], className="mb-1"),
        html.Pre(
            sql_text or "-- Sin SQL disponible",
            className="source-sql-panel",
        ),
    ])

    # Results table
    if not df.empty:
        results_table = dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": get_label(c), "id": c} for c in df.columns],
            page_size=20,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#F5F7FA", "fontWeight": "600",
                "fontSize": "12px", "color": "#6E7191",
            },
            style_cell={
                "fontSize": "12px", "fontFamily": "Inter, sans-serif",
                "padding": "6px 8px", "maxWidth": "200px",
                "overflow": "hidden", "textOverflow": "ellipsis",
            },
            style_data_conditional=[{
                "if": {"row_index": "odd"}, "backgroundColor": "#FAFBFC",
            }],
        )
    else:
        results_table = html.Div([
            html.I(className="bi bi-database display-4 text-muted"),
            html.P("Sin datos para mostrar.", className="text-muted mt-3"),
        ], className="text-center py-4")

    right_panel = html.Div([sql_panel, html.Hr(className="my-2"), results_table])

    # Metadata badges
    badges = []
    if ai_function:
        badges.append(dbc.Badge(f"Funcion: {ai_function}", color="primary", className="me-2"))
    if not df.empty:
        badges.append(dbc.Badge(f"{len(df)} filas x {len(df.columns)} columnas", color="info", className="me-2"))
    if query_details and query_details.get("sql"):
        badges.append(dbc.Badge("SQL Ad-hoc", color="warning", className="me-2"))

    elements.append(html.Div(badges, className="mb-2"))
    elements.append(
        dbc.Row([
            dbc.Col(sidebar, md=3, className="source-sidebar-col"),
            dbc.Col(right_panel, md=9),
        ], className="g-2")
    )

    return html.Div(elements)


# --- Main chat callback ---

@callback(
    Output("chat-messages", "children"),
    Output("results-container", "children"),
    Output("source-data-container", "children"),
    Output("chat-input", "value"),
    Output("chat-history", "data"),
    Output("query-result", "data"),
    Output("download-csv-btn", "disabled"),
    Output("save-query-btn", "disabled"),
    Output("chart-type-toolbar", "style"),
    Output("current-chart-type", "data"),
    Input("chat-send-btn", "n_clicks"),
    Input("chat-input", "n_submit"),
    State("chat-input", "value"),
    State("tenant-context", "data"),
    State("chat-history", "data"),
    prevent_initial_call=True,
)
def send_message(n_clicks, n_submit, message, tenant, history):
    if not message or not message.strip():
        raise PreventUpdate

    history = history or []

    # Add user message to history
    history.append({"role": "user", "content": message})

    # Process query via AI agent (or demo mode fallback)
    result = _agent.process_query(
        user_question=message,
        conversation_history=history,
        tenant_filter=tenant,
    )

    explanation = result.get("response", "")
    df = result.get("data") if result.get("data") is not None else pd.DataFrame()
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame()
    chart_type = result.get("chart_type")
    ai_function = None
    query_details = result.get("query_details")
    if query_details:
        ai_function = query_details.get("function")

    # Add assistant response to history (serialize-safe for dcc.Store)
    assistant_entry = {
        "role": "assistant",
        "content": explanation,
        "has_data": not df.empty,
        "row_count": len(df),
        "ai_function": ai_function,
        "chart_type": chart_type,
    }
    history.append(assistant_entry)

    # Render chat messages
    chat_elements = []
    for msg in history:
        if msg["role"] == "user":
            chat_elements.append(_render_user_message(msg["content"]))
        else:
            chat_elements.append(_render_assistant_message(msg["content"]))

    # Render results panel
    results = _build_results_panel(df, chart_type, query_details)

    # Build source-data tab content (Redash-style)
    source_content = _build_source_tab(df, ai_function, query_details, tenant=tenant)

    # Store query result for CSV export / save
    query_data = {
        "query_text": message,
        "ai_function": ai_function,
        "chart_type": chart_type,
        "data": df.to_dict("records") if not df.empty else [],
        "columns": list(df.columns) if not df.empty else [],
        "row_count": len(df),
        "explanation": explanation,
        "query_details": query_details,
    }

    has_data = not df.empty
    # Show chart type toolbar only when there is data with 2+ columns
    show_toolbar = {"display": "block"} if has_data and len(df.columns) >= 2 else {"display": "none"}

    return (
        chat_elements, results, source_content, "", history, query_data,
        not has_data, not has_data, show_toolbar, chart_type,
    )


# --- Chart type selector ---

@callback(
    Output("results-container", "children", allow_duplicate=True),
    Output("current-chart-type", "data", allow_duplicate=True),
    Input({"type": "chart-type-btn", "index": ALL}, "n_clicks"),
    State("query-result", "data"),
    prevent_initial_call=True,
)
def change_chart_type(n_clicks_list, query_data):
    """Regenerate chart when user clicks a chart type button."""
    if not any(n_clicks_list) or not query_data or not query_data.get("data"):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        raise PreventUpdate

    idx = triggered["index"]
    if idx < 0 or idx >= len(CHART_TYPE_LIST):
        raise PreventUpdate

    selected_type = CHART_TYPE_LIST[idx]
    df = pd.DataFrame(query_data["data"])
    if df.empty:
        raise PreventUpdate

    query_details = query_data.get("query_details")
    results = _build_results_panel(df, selected_type, query_details)

    return results, selected_type


# --- Suggestion chips ---

@callback(
    Output("chat-input", "value", allow_duplicate=True),
    Output("chat-send-btn", "n_clicks"),
    [Input({"type": "suggestion-chip", "index": ALL}, "n_clicks")],
    State("chat-send-btn", "n_clicks"),
    prevent_initial_call=True,
)
def click_suggestion(chip_clicks, current_n):
    """When a suggestion chip is clicked, fill the input and trigger send."""
    if not any(chip_clicks):
        raise PreventUpdate

    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict):
        idx = triggered["index"]
        if 0 <= idx < len(SUGGESTIONS):
            return SUGGESTIONS[idx], (current_n or 0) + 1

    raise PreventUpdate


# --- CSV Export ---

@callback(
    Output("download-csv", "data"),
    Input("download-csv-btn", "n_clicks"),
    State("query-result", "data"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, query_data):
    if not query_data or not query_data.get("data"):
        raise PreventUpdate

    df = pd.DataFrame(query_data["data"])
    return dcc.send_data_frame(df.to_csv, "consulta_resultado.csv", index=False)


# --- Save Query (with conversation history) ---

@callback(
    Output("save-query-btn", "children"),
    Input("save-query-btn", "n_clicks"),
    State("query-result", "data"),
    State("chat-history", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def save_query(n_clicks, query_data, chat_history, tenant):
    if not query_data or not query_data.get("data"):
        raise PreventUpdate

    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    df = pd.DataFrame(query_data["data"])

    name = query_data.get("query_text", "Consulta")[:80]
    generated_sql = None
    if query_data.get("query_details") and query_data["query_details"].get("sql"):
        generated_sql = query_data["query_details"]["sql"]

    result = svc.save_query(
        name=name,
        query_text=query_data["query_text"],
        data=df,
        ai_function=query_data.get("ai_function"),
        generated_sql=generated_sql,
        visualizations=[{"type": query_data.get("chart_type") or "table", "is_default": True}],
        conversation_history=chat_history,
    )

    if result.get("success"):
        return [html.I(className="bi bi-check me-1"), "Guardado"]
    return [html.I(className="bi bi-bookmark me-1"), "Guardar"]


# --- Re-run from URL (with conversation restoration) ---

@callback(
    Output("chat-input", "value", allow_duplicate=True),
    Output("chat-send-btn", "n_clicks", allow_duplicate=True),
    Output("chat-messages", "children", allow_duplicate=True),
    Output("chat-history", "data", allow_duplicate=True),
    Input("query-url", "search"),
    State("chat-send-btn", "n_clicks"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def rerun_from_url(search, current_n, tenant):
    """If URL has ?rerun=<id> or ?q=<text>, load the query and auto-execute."""
    if not search:
        raise PreventUpdate

    import urllib.parse
    params = urllib.parse.parse_qs(search.lstrip("?"))

    # ?rerun=<id> — re-execute a saved query, restore conversation if available
    rerun_id = params.get("rerun", [None])[0]
    if rerun_id:
        svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
        query = svc.get_query(int(rerun_id))
        if not query:
            raise PreventUpdate

        # Check if conversation history is saved
        conv_history = query.get("conversation_history")
        if conv_history and isinstance(conv_history, list) and len(conv_history) > 0:
            # Restore full conversation
            chat_elements = []
            for msg in conv_history:
                if msg.get("role") == "user":
                    chat_elements.append(_render_user_message(msg["content"]))
                else:
                    chat_elements.append(_render_assistant_message(msg.get("content", "")))

            # Add a separator indicating this is a restored conversation
            chat_elements.append(html.Div([
                html.Hr(className="my-2"),
                html.Small([
                    html.I(className="bi bi-clock-history me-1"),
                    "Conversacion restaurada. Puedes continuar preguntando.",
                ], className="text-muted", style={"fontSize": "11px"}),
            ], className="text-center mb-2"))

            return no_update, no_update, chat_elements, conv_history

        # No conversation history — just re-run the query text
        return query["query_text"], (current_n or 0) + 1, no_update, no_update

    # ?q=<text> — pre-fill a question and auto-execute
    question = params.get("q", [None])[0]
    if question:
        return question, (current_n or 0) + 1, no_update, no_update

    raise PreventUpdate


# --- Toggle history panel ---

@callback(
    Output("query-history-collapse", "is_open"),
    Input("query-history-toggle", "n_clicks"),
    State("query-history-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_history(n_clicks, is_open):
    return not is_open


# --- Load recent history ---

@callback(
    Output("query-recent-history", "children"),
    Input("query-history-toggle", "n_clicks"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def load_recent_history(n_clicks, tenant):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.list_queries(limit=5)

    if not result["queries"]:
        return html.Small("No hay consultas recientes.", className="text-muted")

    items = []
    for q in result["queries"]:
        # Show conversation icon if it has saved history
        has_conv = bool(q.get("conversation_history"))
        items.append(
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Small(q["name"][:60], className="fw-semibold",
                                   style={"fontSize": "12px"}),
                        html.Div([
                            html.I(className="bi bi-chat-left-text text-primary me-2",
                                   style={"fontSize": "10px"},
                                   title="Tiene conversacion guardada") if has_conv else None,
                            dbc.Button(
                                html.I(className="bi bi-arrow-repeat"),
                                href=f"/consultas/nueva?rerun={q['id']}",
                                outline=True, color="primary", size="sm",
                                style={"padding": "2px 6px"},
                            ),
                        ], className="d-flex align-items-center ms-auto"),
                    ], className="d-flex align-items-center"),
                ], className="py-1 px-2"),
            ], className="mb-1", style={"borderRadius": "8px", "border": "1px solid #F0F0F5"})
        )

    return html.Div(items)
