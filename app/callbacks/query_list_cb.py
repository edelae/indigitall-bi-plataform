"""Query list page callbacks — search, filter, favorites, thumbnails, re-run."""

import pandas as pd
from dash import Input, Output, State, callback, html, dcc, ctx, no_update, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px

from app.services.storage_service import StorageService
from app.services.label_service import get_label
from app.config import settings

CHART_COLORS = ["#1E88E5", "#76C043", "#A0A3BD", "#42A5F5", "#1565C0", "#FFC107"]


def _mini_chart(q):
    """Generate a small thumbnail chart from query result data."""
    viz = q.get("visualizations") or []
    chart_type = viz[0].get("type", "table") if viz else "table"
    data = q.get("result_data") or []

    if not data or chart_type == "table":
        return None

    df = pd.DataFrame(data)
    if df.empty or len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]
    if df[y_col].dtype == "object":
        try:
            df = df.copy()
            df[y_col] = pd.to_numeric(
                df[y_col].str.replace(",", "").str.replace("%", ""),
                errors="coerce",
            )
        except Exception:
            return None
        if df[y_col].isna().all():
            return None

    if chart_type == "pie":
        fig = px.pie(df, names=x_col, values=y_col, color_discrete_sequence=CHART_COLORS)
    elif chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col, color_discrete_sequence=CHART_COLORS)
    else:
        fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=CHART_COLORS)

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=0, r=0, t=0, b=0),
        height=80,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"height": "80px"},
    )


def _format_date(dt):
    """Format datetime for display."""
    if not dt:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d %b %Y")
    return str(dt)[:10]


def _query_row(q):
    """Render a single query card with thumbnail, actions, and metadata."""
    query_id = q["id"]
    viz = q.get("visualizations") or []
    chart_type = viz[0].get("type", "table") if viz else "table"
    row_count = q.get("result_row_count", 0)

    # Thumbnail
    thumb = _mini_chart(q)
    thumb_col = dbc.Col(
        thumb if thumb else html.Div(
            html.I(className="bi bi-table", style={"fontSize": "24px", "color": "#A0A3BD"}),
            className="d-flex align-items-center justify-content-center",
            style={"height": "80px"},
        ),
        md=2,
        className="pe-0",
    )

    # Info column
    has_conversation = bool(q.get("conversation_history"))
    info_col = dbc.Col([
        html.Div([
            html.A(
                q["name"][:80],
                href=f"/consultas/nueva?rerun={query_id}",
                className="fw-semibold text-decoration-none",
                style={"color": "#1A1A2E", "fontSize": "14px"},
            ),
        ]),
        html.Small(
            (q.get("query_text") or "")[:120],
            className="text-muted d-block mt-1",
            style={"fontSize": "12px"},
        ),
        html.Div([
            dbc.Badge(chart_type.upper(), color="primary", className="me-1",
                      style={"fontSize": "10px"}),
            dbc.Badge(f"{row_count} filas", color="light", text_color="dark",
                      className="me-1", style={"fontSize": "10px"}),
            dbc.Badge([html.I(className="bi bi-chat-left-text me-1"), "Chat"],
                      color="success", className="me-1",
                      style={"fontSize": "10px"}) if has_conversation else None,
            html.Small(_format_date(q.get("created_at")),
                       className="text-muted", style={"fontSize": "11px"}),
        ], className="mt-1"),
    ], md=6)

    # Actions column
    actions_col = dbc.Col([
        dbc.Button(
            html.I(className="bi bi-star-fill" if q.get("is_favorite") else "bi bi-star"),
            id={"type": "toggle-fav", "index": query_id},
            outline=True,
            color="warning" if q.get("is_favorite") else "secondary",
            size="sm",
            className="me-1",
            title="Favorito",
        ),
        dbc.Button(
            html.I(className="bi bi-play-fill"),
            href=f"/consultas/nueva?rerun={query_id}",
            outline=True,
            color="primary",
            size="sm",
            className="me-1",
            title="Re-ejecutar",
        ),
        dbc.Button(
            html.I(className="bi bi-grid-1x2"),
            href=f"/tableros/nuevo?query_id={query_id}",
            outline=True,
            color="secondary",
            size="sm",
            title="Usar en Tablero",
        ),
    ], md=4, className="text-end d-flex align-items-center justify-content-end")

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([thumb_col, info_col, actions_col],
                    className="align-items-center"),
        ], className="py-2 px-3"),
    ], className="mb-2", style={"borderRadius": "12px", "border": "1px solid #F0F0F5"})


@callback(
    Output("query-list-container", "children"),
    Input("tenant-context", "data"),
    Input("query-search-input", "value"),
    Input("query-favorites-btn", "n_clicks"),
    Input("query-all-btn", "n_clicks"),
    Input({"type": "toggle-fav", "index": ALL}, "n_clicks"),
)
def load_query_list(tenant, search, fav_clicks, all_clicks, toggle_clicks):
    triggered = ctx.triggered_id

    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)

    # Handle favorite toggle
    if isinstance(triggered, dict) and triggered.get("type") == "toggle-fav":
        query_id = triggered["index"]
        svc.toggle_favorite_query(query_id)

    # Determine filter mode
    favorites_only = triggered == "query-favorites-btn"

    result = svc.list_queries(
        favorites_only=favorites_only,
        search=search if search else None,
        limit=50,
    )

    if not result["queries"]:
        msg = "No hay consultas favoritas." if favorites_only else (
            f"No se encontraron consultas para \"{search}\"." if search else
            "Aun no hay consultas guardadas. Crea tu primera consulta con el asistente IA."
        )
        return html.Div([
            html.I(className="bi bi-search display-4 text-muted"),
            html.P(msg, className="text-muted mt-3"),
            dbc.Button(
                [html.I(className="bi bi-plus-lg me-1"), "Nueva Consulta"],
                href="/consultas/nueva", color="primary", className="mt-2",
            ),
        ], className="text-center py-5")

    rows = [_query_row(q) for q in result["queries"]]
    rows.append(
        html.Small(
            f"Mostrando {len(result['queries'])} de {result['total']}",
            className="text-muted",
        )
    )

    return html.Div(rows)
