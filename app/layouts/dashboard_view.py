"""Dashboard view page — Widget grid display with info modals."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(
    __name__,
    path_template="/tableros/saved/<dashboard_id>",
    name="Tablero",
    order=39,
)


def layout(dashboard_id=None, **kwargs):
    edit_href = f"/tableros/nuevo?edit={dashboard_id}" if dashboard_id else "/tableros/nuevo"

    return dbc.Container([
        # Stores
        dcc.Store(id="dv-dashboard-id", data=dashboard_id),
        dcc.Store(id="dv-cross-filter", storage_type="session"),

        # Dashboard header
        html.Div([
            html.Div([
                html.H2(id="dv-title", children=(
                    f"Tablero #{dashboard_id}" if dashboard_id else "Tablero"
                ), className="page-title mb-0"),
                html.Small(id="dv-subtitle", children="Cargando...",
                           className="text-muted"),
            ]),
            html.Div([
                dbc.Button(
                    [html.I(className="bi bi-pencil me-1"), "Editar"],
                    href=edit_href,
                    outline=True, color="secondary", size="sm", className="me-2",
                ),
                dbc.Button(html.I(className="bi bi-star"),
                           id="dv-fav-btn",
                           outline=True, color="warning", size="sm"),
            ]),
        ], className="d-flex justify-content-between align-items-start mb-4"),

        # Cross-filter badge
        html.Div(id="dv-filter-badge"),

        # Widget grid
        html.Div(id="dashboard-grid", className="dashboard-grid"),

        # Info modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="dv-info-modal-title")),
            dbc.ModalBody(id="dv-info-modal-body"),
        ], id="dv-info-modal", size="lg"),

        # Floating AI chat button
        dbc.Button(
            [html.I(className="bi bi-chat-dots me-1"), "Preguntar"],
            id="open-ai-chat",
            color="primary",
            className="fab-chat-btn",
        ),

        # AI Chat slide-over (Offcanvas)
        dbc.Offcanvas(
            html.Div("Chat IA integrado — proximamente.", className="p-3 text-muted"),
            id="ai-chat-offcanvas",
            title="Asistente IA",
            placement="end",
            style={"width": "400px"},
        ),
    ], fluid=True, className="py-4")
