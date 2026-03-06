"""Query page — AI chat (left) + Results (right) + chart type selector + Redash-style source panel."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/consultas/nueva", name="Nueva Consulta", order=1)

# Suggestion chips (common questions in Spanish)
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

# Chart type options for the toolbar
CHART_TYPES = [
    {"type": "bar", "icon": "bi-bar-chart", "label": "Barras"},
    {"type": "line", "icon": "bi-graph-up", "label": "Linea"},
    {"type": "pie", "icon": "bi-pie-chart", "label": "Torta"},
    {"type": "area", "icon": "bi-graph-down", "label": "Area"},
    {"type": "histogram", "icon": "bi-bar-chart-steps", "label": "Histograma"},
    {"type": "table", "icon": "bi-table", "label": "Tabla"},
]

layout = dbc.Container([
    # URL location for re-run support
    dcc.Location(id="query-url", refresh=False),

    # Store for current chart type selection
    dcc.Store(id="current-chart-type", data=None),

    dbc.Row([
        # Left panel: AI Chat (35%)
        dbc.Col([
            html.Div([
                html.H5([html.I(className="bi bi-chat-dots me-2"), "Asistente IA"],
                         className="panel-title"),

                # Suggestion chips (shown when no messages)
                html.Div(
                    [dbc.Button(s, outline=True, color="primary", size="sm",
                                className="suggestion-chip me-2 mb-2",
                                id={"type": "suggestion-chip", "index": i})
                     for i, s in enumerate(SUGGESTIONS)],
                    id="suggestion-chips",
                    className="mb-3",
                ),

                # Chat messages container (with welcome message)
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-robot me-2"),
                            dcc.Markdown(
                                "Hola! Soy tu asistente de analitica. Preguntame sobre "
                                "tus datos de WhatsApp: mensajes, agentes, contactos, "
                                "tendencias y mas. Selecciona una sugerencia o escribe tu pregunta.",
                                className="d-inline",
                            ),
                        ], className="chat-message assistant-msg"),
                    ], className="mb-3"),
                ], id="chat-messages", className="chat-messages-container"),

                # Chat input
                dbc.InputGroup([
                    dbc.Input(
                        id="chat-input",
                        placeholder="Haz una pregunta sobre tus datos...",
                        type="text",
                        className="chat-input-field",
                    ),
                    dbc.Button(
                        html.I(className="bi bi-send"),
                        id="chat-send-btn",
                        color="primary",
                        className="chat-send-btn",
                    ),
                ], className="chat-input-group"),
            ], className="chat-panel"),

            # Recent history panel (collapsible)
            html.Div([
                html.Hr(className="my-3"),
                dbc.Button(
                    [html.I(className="bi bi-clock-history me-2"), "Historial Reciente"],
                    id="query-history-toggle",
                    outline=True, color="secondary", size="sm",
                    className="w-100 mb-2",
                    style={"borderRadius": "8px"},
                ),
                dbc.Collapse(
                    html.Div(id="query-recent-history", className="mt-2"),
                    id="query-history-collapse",
                    is_open=False,
                ),
            ]),
        ], width=5, className="chat-column"),

        # Right panel: Results (65%)
        dbc.Col([
            html.Div([
                html.Div([
                    html.H5("Resultados", className="panel-title"),
                    html.Div([
                        dbc.Button([html.I(className="bi bi-download me-1"), "CSV"],
                                   outline=True, color="secondary", size="sm",
                                   className="me-2", id="download-csv-btn", disabled=True),
                        dbc.Button([html.I(className="bi bi-bookmark me-1"), "Guardar"],
                                   color="primary", size="sm",
                                   id="save-query-btn", disabled=True),
                    ]),
                ], className="d-flex justify-content-between align-items-center mb-3"),

                # Chart type selector toolbar (hidden until there are results)
                html.Div(
                    dbc.ButtonGroup([
                        dbc.Button(
                            [html.I(className=f"bi {ct['icon']} me-1"), ct["label"]],
                            id={"type": "chart-type-btn", "index": i},
                            outline=True, color="secondary", size="sm",
                            className="chart-type-btn",
                        )
                        for i, ct in enumerate(CHART_TYPES)
                    ], size="sm"),
                    id="chart-type-toolbar",
                    className="mb-3",
                    style={"display": "none"},
                ),

                # Tabs: Resultado + Fuente de Datos
                dbc.Tabs([
                    dbc.Tab(
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-chat-square-text display-4 text-muted"),
                                html.P("Los resultados de tu consulta apareceran aqui.",
                                       className="text-muted mt-3"),
                            ], className="text-center py-5"),
                        ], id="results-container", className="results-panel"),
                        label="Resultado",
                        tab_id="tab-resultado",
                    ),
                    dbc.Tab(
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-database display-4 text-muted"),
                                html.P("Ejecuta una consulta para ver la fuente de datos.",
                                       className="text-muted mt-3"),
                            ], className="text-center py-5"),
                        ], id="source-data-container", className="results-panel"),
                        label="Fuente de Datos",
                        tab_id="tab-fuente",
                    ),
                ], id="results-tabs", active_tab="tab-resultado", className="mb-3"),

            ], className="results-wrapper"),
        ], width=7, className="results-column"),
    ], className="g-3 query-page-row"),

    # Download component
    dcc.Download(id="download-csv"),

], fluid=True, className="py-3 query-page")
