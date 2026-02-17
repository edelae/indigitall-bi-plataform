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
from app.config import settings

# Chart color sequence from design system
CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107", "#9C27B0", "#FF5722"]

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
    """Generate a simple chart from a DataFrame based on its shape."""
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

    if chart_type == "line" or "date" in x_col.lower() or "fecha" in x_col.lower():
        fig = px.line(df, x=x_col, y=y_col, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "pie" or len(df) <= 8:
        fig = px.pie(df, names=x_col, values=y_col, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "bar" or df[y_col].dtype in ("int64", "float64"):
        fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=CHART_COLORS)
    else:
        fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=CHART_COLORS)

    fig.update_layout(
        template="plotly_white",
        font_family="Inter, sans-serif",
        margin=dict(l=20, r=20, t=30, b=20),
        height=350,
    )
    return fig


# --- Main chat callback ---

@callback(
    Output("chat-messages", "children"),
    Output("results-container", "children"),
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
                columns=[{"name": c, "id": c} for c in df.columns],
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

    # Store query result for CSV export / save
    query_data = {
        "query_text": message,
        "ai_function": ai_function,
        "chart_type": chart_type,
        "data": df.to_dict("records") if not df.empty else [],
        "columns": list(df.columns) if not df.empty else [],
        "row_count": len(df),
        "explanation": explanation,
    }

    has_data = not df.empty
    return chat_elements, results, "", history, query_data, not has_data, not has_data


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
        from app.layouts.query import SUGGESTIONS
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
    result = svc.save_query(
        name=name,
        query_text=query_data["query_text"],
        data=df,
        ai_function=query_data.get("ai_function"),
        visualizations=[{"type": query_data.get("chart_type") or "table", "is_default": True}],
    )

    if result.get("success"):
        return [html.I(className="bi bi-check me-1"), "Guardado"]
    return [html.I(className="bi bi-bookmark me-1"), "Guardar"]
