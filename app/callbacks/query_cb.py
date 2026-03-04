"""
Query page callbacks — AI chat interaction, results rendering, save/export.

This is the core interaction page: user asks questions in the chat panel,
AI processes them, results appear in the right panel with table + chart.
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
from app.services.label_service import get_label
from app.config import settings

# Chart color sequence from design system
CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107", "#9C27B0", "#FF5722"]

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

    # Determine chart type: AI-suggested > auto-detect
    if not chart_type:
        x_lower = x_col.lower()
        if any(kw in x_lower for kw in ["date", "fecha", "time", "dia", "mes", "month"]):
            chart_type = "line"
        elif len(df) <= 8 and len(df.columns) == 2:
            chart_type = "pie"
        else:
            chart_type = "bar"

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


def _get_source_table_name(ai_function):
    """Map AI function names to their source database table."""
    TABLE_MAP = {
        "summary": "messages",
        "fallback_rate": "messages",
        "messages_by_direction": "messages",
        "messages_by_hour": "messages",
        "messages_over_time": "messages",
        "messages_by_day_of_week": "messages",
        "top_contacts": "messages",
        "intent_distribution": "messages",
        "agent_performance": "messages",
        "entity_comparison": "messages",
        "high_messages_day": "messages",
        "high_messages_week": "messages",
        "high_messages_month": "messages",
    }
    return TABLE_MAP.get(ai_function, "messages")


def _fetch_full_source_table(table_name, tenant):
    """Fetch full source table with all columns (limited to 200 rows)."""
    from sqlalchemy import text as sa_text
    from app.models.database import engine as db_engine
    try:
        safe_tables = {
            "messages", "contacts", "agents", "daily_stats",
            "chat_conversations", "chat_channels", "chat_topics",
            "campaigns", "toques_daily", "toques_heatmap", "toques_usuario",
            "fact_message_events", "dim_date", "dim_time", "dim_channel",
            "dim_event_type", "dim_tenant", "dim_contact", "dim_agent",
            "dim_campaign", "dim_conversation",
        }
        if table_name not in safe_tables:
            table_name = "messages"

        sql = f"SELECT * FROM {table_name}"
        if tenant:
            sql += f" WHERE tenant_id = :tenant"
        sql += " ORDER BY 1 DESC LIMIT 200"

        with db_engine.connect() as conn:
            if tenant:
                return pd.read_sql(sa_text(sql), conn, params={"tenant": tenant})
            return pd.read_sql(sa_text(sql), conn)
    except Exception:
        return pd.DataFrame()


def _build_source_tab(df, ai_function, query_details, tenant=None):
    """Build the 'Fuente de Datos' tab showing the FULL source table."""
    if df.empty:
        return html.Div([
            html.I(className="bi bi-database display-4 text-muted"),
            html.P("Sin datos para mostrar.", className="text-muted mt-3"),
        ], className="text-center py-5")

    from dash import dash_table

    # Determine source table and fetch ALL columns
    if query_details and query_details.get("sql"):
        # For ad-hoc SQL, extract table name from query
        import re
        match = re.search(r"FROM\s+(\w+)", query_details["sql"], re.IGNORECASE)
        source_table = match.group(1) if match else "messages"
    else:
        source_table = _get_source_table_name(ai_function)

    full_df = _fetch_full_source_table(source_table, tenant)
    if full_df.empty:
        full_df = df  # Fallback to result df if source fetch fails

    elements = []

    # Metadata badges
    badges = []
    badges.append(dbc.Badge(f"Tabla: {source_table}", color="dark", className="me-2"))
    if ai_function:
        badges.append(dbc.Badge(f"Funcion: {ai_function}", color="primary", className="me-2"))
    badges.append(dbc.Badge(
        f"{len(full_df)} filas x {len(full_df.columns)} columnas",
        color="info", className="me-2",
    ))
    if query_details and query_details.get("sql"):
        badges.append(dbc.Badge("SQL Ad-hoc", color="warning", className="me-2"))
    elements.append(html.Div(badges, className="mb-3"))

    # Column schema table (from the FULL source table)
    schema_rows = []
    for col in full_df.columns:
        dtype = str(full_df[col].dtype)
        nulls = int(full_df[col].isna().sum())
        unique = int(full_df[col].nunique())
        schema_rows.append({
            "columna": col,
            "label": get_label(col),
            "tipo": dtype,
            "nulos": nulls,
            "unicos": unique,
        })

    elements.append(html.H6("Esquema de Columnas (tabla completa)", className="mt-2 mb-2"))
    elements.append(
        dash_table.DataTable(
            data=schema_rows,
            columns=[
                {"name": "Columna", "id": "columna"},
                {"name": "Label", "id": "label"},
                {"name": "Tipo", "id": "tipo"},
                {"name": "Nulos", "id": "nulos"},
                {"name": "Unicos", "id": "unicos"},
            ],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#F5F7FA",
                "fontWeight": "600",
                "fontSize": "12px",
            },
            style_cell={"fontSize": "12px", "fontFamily": "Inter, sans-serif", "padding": "6px 8px"},
        )
    )

    # SQL query if ad-hoc
    if query_details and query_details.get("sql"):
        elements.append(html.H6("SQL Ejecutado", className="mt-3 mb-2"))
        elements.append(html.Pre(query_details["sql"], className="bg-light p-3 rounded small"))

    # Full source table data with ALL columns
    elements.append(html.H6(
        f"Datos Completos — {source_table} (primeras {len(full_df)} filas)",
        className="mt-3 mb-2",
    ))
    elements.append(
        dash_table.DataTable(
            data=full_df.to_dict("records"),
            columns=[{"name": get_label(c), "id": c} for c in full_df.columns],
            page_size=20,
            sort_action="native",
            filter_action="native",
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
                "maxWidth": "200px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            style_data_conditional=[{
                "if": {"row_index": "odd"},
                "backgroundColor": "#FAFBFC",
            }],
        )
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
    results = []
    if not df.empty:
        # Chart (if applicable)
        fig = _auto_chart(df, chart_type)
        if fig:
            results.append(dcc.Graph(figure=fig, className="mb-3"))

        # Data table
        from dash import dash_table
        results.append(
            dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[{"name": get_label(c), "id": c} for c in df.columns],
                page_size=15,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#F5F7FA",
                    "fontWeight": "600",
                    "fontSize": "13px",
                    "color": "#6E7191",
                    "textTransform": "uppercase",
                },
                style_cell={
                    "fontSize": "13px",
                    "fontFamily": "Inter, sans-serif",
                    "padding": "8px 12px",
                },
                style_data_conditional=[{
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#FAFBFC",
                }],
            )
        )

        results.append(html.Small(f"{len(df)} filas", className="text-muted mt-2 d-block"))

        # Show SQL details if it was an ad-hoc query
        if query_details and query_details.get("sql"):
            results.append(
                dbc.Accordion([
                    dbc.AccordionItem(
                        html.Pre(
                            query_details["sql"],
                            className="bg-light p-3 rounded small",
                        ),
                        title="Ver SQL generado",
                    ),
                ], start_collapsed=True, className="mt-2")
            )
    else:
        results.append(html.Div([
            html.I(className="bi bi-info-circle display-4 text-muted"),
            html.P(explanation, className="text-muted mt-3"),
        ], className="text-center py-5"))

    # Build source-data tab content (full source table with all columns)
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
    return chat_elements, results, source_content, "", history, query_data, not has_data, not has_data


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


# --- Save Query ---

@callback(
    Output("save-query-btn", "children"),
    Input("save-query-btn", "n_clicks"),
    State("query-result", "data"),
    State("tenant-context", "data"),
    prevent_initial_call=True,
)
def save_query(n_clicks, query_data, tenant):
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
    )

    if result.get("success"):
        return [html.I(className="bi bi-check me-1"), "Guardado"]
    return [html.I(className="bi bi-bookmark me-1"), "Guardar"]


# --- Re-run from URL ---

@callback(
    Output("chat-input", "value", allow_duplicate=True),
    Output("chat-send-btn", "n_clicks", allow_duplicate=True),
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

    # ?rerun=<id> — re-execute a saved query
    rerun_id = params.get("rerun", [None])[0]
    if rerun_id:
        svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
        query = svc.get_query(int(rerun_id))
        if not query:
            raise PreventUpdate
        return query["query_text"], (current_n or 0) + 1

    # ?q=<text> — pre-fill a question and auto-execute
    question = params.get("q", [None])[0]
    if question:
        return question, (current_n or 0) + 1

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
        items.append(
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Small(q["name"][:60], className="fw-semibold",
                                   style={"fontSize": "12px"}),
                        dbc.Button(
                            html.I(className="bi bi-arrow-repeat"),
                            href=f"/consultas/nueva?rerun={q['id']}",
                            outline=True, color="primary", size="sm",
                            className="ms-auto",
                            style={"padding": "2px 6px"},
                        ),
                    ], className="d-flex align-items-center"),
                ], className="py-1 px-2"),
            ], className="mb-1", style={"borderRadius": "8px", "border": "1px solid #F0F0F5"})
        )

    return html.Div(items)
