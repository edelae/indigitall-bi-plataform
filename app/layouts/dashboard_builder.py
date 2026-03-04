"""Dashboard Builder — Create custom dashboards from saved queries."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/tableros/nuevo", name="Nuevo Tablero", order=38)

layout = dbc.Container([
    # URL for query_id param
    dcc.Location(id="builder-url", refresh=False),

    # Stores
    dcc.Store(id="builder-widgets", storage_type="session", data=[]),
    dcc.Store(id="builder-dashboard-id", storage_type="session"),
    dcc.Store(id="builder-ai-suggestions", storage_type="memory", data=[]),

    # Top bar: name + description + save
    dbc.Row([
        dbc.Col([
            dbc.Input(
                id="builder-name",
                placeholder="Nombre del tablero...",
                value="",
                className="mb-2",
                style={"fontSize": "18px", "fontWeight": "600", "border": "none",
                        "borderBottom": "2px solid #E4E4E7", "borderRadius": "0",
                        "padding": "8px 4px"},
            ),
            dbc.Input(
                id="builder-description",
                placeholder="Descripcion (opcional)...",
                value="",
                size="sm",
                style={"border": "none", "borderBottom": "1px solid #F0F0F5",
                        "borderRadius": "0", "fontSize": "13px", "color": "#6E7191"},
            ),
        ], md=8),
        dbc.Col([
            dbc.Button(
                [html.I(className="bi bi-check-lg me-1"), "Guardar Tablero"],
                id="builder-save-btn",
                color="primary",
                className="me-2",
                style={"borderRadius": "8px"},
            ),
            dbc.Button(
                [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                href="/tableros",
                outline=True,
                color="secondary",
                style={"borderRadius": "8px"},
            ),
        ], md=4, className="text-end d-flex align-items-start justify-content-end"),
    ], className="mb-4 align-items-start"),

    # Save feedback
    html.Div(id="builder-save-feedback"),

    # Main content: panel lateral + canvas
    dbc.Row([
        # Left panel: available queries (md=3)
        dbc.Col([
            html.H6([html.I(className="bi bi-collection me-2"), "Consultas Guardadas"],
                     className="mb-3", style={"fontWeight": "600", "color": "#1A1A2E"}),
            html.Div(id="builder-query-list", children=[
                html.Div([
                    html.I(className="bi bi-hourglass-split text-muted"),
                    html.Small(" Cargando consultas...", className="text-muted"),
                ], className="text-center py-4"),
            ]),
        ], md=3, style={
            "borderRight": "1px solid #F0F0F5",
            "paddingRight": "16px",
            "maxHeight": "calc(100vh - 200px)",
            "overflowY": "auto",
        }),

        # Right canvas: widget grid (md=9)
        dbc.Col([
            html.Div(id="builder-canvas", children=[
                html.Div([
                    html.I(className="bi bi-grid-1x2 display-4 text-muted"),
                    html.P("Agrega consultas desde el panel lateral para crear widgets.",
                           className="text-muted mt-3"),
                    html.P("Tambien puedes usar el asistente IA para sugerencias.",
                           className="text-muted", style={"fontSize": "13px"}),
                ], className="text-center py-5",
                   id="builder-empty-state"),
            ]),
        ], md=9, style={"paddingLeft": "24px"}),
    ], className="g-0"),

    # FAB for AI assistant
    dbc.Button(
        [html.I(className="bi bi-stars me-1"), "Asistente IA"],
        id="builder-ai-fab",
        color="primary",
        className="fab-chat-btn",
        style={
            "position": "fixed", "bottom": "24px", "right": "24px",
            "borderRadius": "24px", "padding": "10px 20px",
            "boxShadow": "0 4px 16px rgba(30,136,229,0.3)",
            "zIndex": "1000",
        },
    ),

    # AI Chat Offcanvas
    dbc.Offcanvas([
        dbc.InputGroup([
            dbc.Input(
                id="builder-ai-input",
                placeholder="Ej: Quiero ver tendencia de mensajes y top contactos...",
                type="text",
            ),
            dbc.Button(
                html.I(className="bi bi-send"),
                id="builder-ai-send",
                color="primary",
            ),
        ], className="mb-3"),
        html.Div(id="builder-ai-chat", children=[
            html.Div([
                html.I(className="bi bi-stars me-2", style={"color": "#1E88E5"}),
                html.Small(
                    "Describeme que metricas quieres ver y te sugerire las consultas "
                    "mas relevantes para tu tablero.",
                    className="text-muted",
                ),
            ], className="p-3", style={"backgroundColor": "#F5F7FA", "borderRadius": "12px"}),
        ]),
    ],
        id="builder-ai-offcanvas",
        title="Asistente IA para Tableros",
        placement="end",
        style={"width": "420px"},
    ),

    # SQL Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="builder-sql-modal-title")),
        dbc.ModalBody([
            html.Div(id="builder-sql-modal-body"),
        ]),
    ], id="builder-sql-modal", size="lg"),

], fluid=True, className="py-4")
