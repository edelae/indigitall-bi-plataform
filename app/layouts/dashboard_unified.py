"""Dashboard Unificado — Gallery + restructured tabs with WhatsApp sub-tabs."""

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/tableros", name="Tableros", order=3)

TABLE_STYLE = {
    "cell": {
        "textAlign": "left", "padding": "10px 14px",
        "fontFamily": "Inter, sans-serif", "fontSize": "13px",
        "color": "#1A1A2E",
    },
    "header": {
        "backgroundColor": "#F5F7FA", "fontWeight": "600",
        "borderBottom": "2px solid #E4E4E7", "color": "#6E7191",
        "fontSize": "12px", "textTransform": "uppercase",
        "letterSpacing": "0.04em", "padding": "10px 14px",
    },
    "data": {"borderBottom": "1px solid #F0F0F5"},
    "conditional": [{"if": {"row_index": "odd"}, "backgroundColor": "#FAFBFC"}],
}


def _section_label(text):
    return html.Div(text, className="section-label mb-2 mt-4",
                     style={"fontSize": "13px", "fontWeight": "600",
                            "color": "#6E7191", "letterSpacing": "0.06em"})


def _chart_card(title, graph_id, md=6):
    return dbc.Col(
        dbc.Card([
            dbc.CardHeader(title, style={
                "fontSize": "14px", "fontWeight": "600", "color": "#1A1A2E",
                "backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                "padding": "14px 20px",
            }),
            dbc.CardBody(dcc.Loading(dcc.Graph(
                id=graph_id, config={"displayModeBar": False},
                style={"height": "320px"},
            )), style={"padding": "12px 16px"}),
        ], className="chart-widget", style={
            "borderRadius": "16px", "border": "1px solid #F0F0F5",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.04)",
        }),
        md=md,
    )


def _data_table(table_id, page_size=10, filterable=False):
    return dash_table.DataTable(
        id=table_id,
        sort_action="native",
        filter_action="native" if filterable else "none",
        page_size=page_size,
        style_table={"overflowX": "auto"},
        style_cell=TABLE_STYLE["cell"],
        style_header=TABLE_STYLE["header"],
        style_data=TABLE_STYLE["data"],
        style_data_conditional=TABLE_STYLE["conditional"],
    )


def _csv_button(btn_id):
    return dbc.Button(
        [html.I(className="bi bi-download me-1"), "CSV"],
        id=btn_id, outline=True, color="secondary", size="sm",
        className="float-end",
        style={"borderRadius": "8px", "fontSize": "12px"},
    )


def _disabled_tab_content(icon, channel_name):
    return html.Div(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {icon}",
                           style={"fontSize": "48px", "color": "#A0A3BD"}),
                ], className="text-center mb-3 mt-4"),
                html.H4("Canal no disponible", className="text-center",
                         style={"color": "#6E7191", "fontWeight": "600"}),
                html.P(
                    f"El canal {channel_name} no esta habilitado para esta cuenta. "
                    "Los datos se mostraran automaticamente cuando sea activado.",
                    className="text-center",
                    style={"color": "#A0A3BD", "fontSize": "14px"},
                ),
            ]),
        ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                   "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
        className="py-5",
    )


# ===================== Gallery View =====================

def _build_gallery():
    return html.Div(id="ud-gallery", children=[
        dbc.Row([
            dbc.Col([
                html.H2("Tableros", className="page-title"),
                html.P("Selecciona un tablero para explorar", className="page-subtitle"),
            ]),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(
                html.Div(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="bi bi-grid-1x2-fill",
                                       style={"fontSize": "32px", "color": "#1E88E5"}),
                            ], className="mb-3"),
                            html.H5("VISIONAMOS", style={"fontWeight": "600", "color": "#1A1A2E"}),
                            html.P("Dashboard analitico multicanal — WhatsApp, SMS, Contact Center",
                                   style={"fontSize": "13px", "color": "#6E7191"}),
                            html.Div([
                                html.Span("8 secciones", className="badge bg-primary me-2",
                                          style={"fontSize": "11px"}),
                                html.Span("Activo", className="badge bg-success",
                                          style={"fontSize": "11px"}),
                            ], className="mt-2"),
                            dbc.Button(
                                [html.I(className="bi bi-arrow-right me-2"), "Ver Dashboard"],
                                id="ud-gallery-card-visionamos",
                                color="primary", size="sm", className="mt-3",
                                style={"borderRadius": "8px"},
                            ),
                        ], style={"padding": "24px"}),
                    ], style={
                        "borderRadius": "16px", "cursor": "pointer",
                        "border": "2px solid #E4E4E7",
                        "transition": "all 0.2s ease",
                    }, className="hover-shadow"),
                ),
                md=4, sm=6, xs=12,
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="bi bi-plus-circle-dotted",
                                   style={"fontSize": "32px", "color": "#A0A3BD"}),
                        ], className="mb-3"),
                        html.H5("Nuevo Tablero", style={"fontWeight": "600", "color": "#A0A3BD"}),
                        html.P("Crea un tablero personalizado con tus metricas",
                               style={"fontSize": "13px", "color": "#A0A3BD"}),
                    ], style={"padding": "24px"}),
                ], style={
                    "borderRadius": "16px", "cursor": "pointer",
                    "border": "2px dashed #E4E4E7",
                }),
                md=4, sm=6, xs=12,
            ),
        ], className="g-3"),
    ])


# ===================== Dashboard Container =====================

def _build_dashboard():
    return html.Div(id="ud-dashboard", style={"display": "none"}, children=[
        # Back button + header
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="bi bi-arrow-left me-2"),
                    "Volver a Tableros",
                ], id="ud-back-to-gallery", outline=True, color="secondary", size="sm",
                   style={"borderRadius": "8px"}),
            ], width="auto"),
            dbc.Col([
                html.H2("Dashboard VISIONAMOS", className="page-title mb-0"),
                html.P("Vista unificada de todos los canales",
                       className="page-subtitle mb-0",
                       style={"fontSize": "13px", "color": "#6E7191"}),
            ]),
        ], className="mb-3 align-items-center"),

        # Date selector
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("7D", id="ud-btn-7d", outline=True,
                               color="primary", size="sm"),
                    dbc.Button("30D", id="ud-btn-30d", outline=True,
                               color="primary", size="sm", active=True),
                    dbc.Button("90D", id="ud-btn-90d", outline=True,
                               color="primary", size="sm"),
                    dbc.Button("Custom", id="ud-btn-custom", outline=True,
                               color="primary", size="sm"),
                ], style={"borderRadius": "8px"}),
                dcc.DatePickerRange(
                    id="ud-date-picker",
                    display_format="YYYY-MM-DD",
                    style={"display": "none"},
                    className="ms-3",
                ),
            ], className="d-flex align-items-center"),
        ], className="mb-4"),

        dcc.Store(id="ud-date-store", storage_type="session"),

        # Tabs
        dbc.Tabs(
            id="ud-tabs",
            active_tab="tab-general",
            className="ud-tabs",
            children=[
                _build_general_tab(),
                _build_whatsapp_tab(),
                _build_sms_tab(),
                _build_toques_tab(),
                _build_email_tab(),
                _build_push_tab(),
                _build_inapp_tab(),
                _build_cc_tab(),
                _build_wallet_tab(),
            ],
        ),
    ])


# ===================== Tab 1: General =====================

def _build_general_tab():
    return dbc.Tab(label="General", tab_id="tab-general", children=[
        _section_label("RESUMEN GENERAL"),
        dbc.Row(id="ud-gen-kpi-row", className="mb-4 g-3"),
        _section_label("FUNNEL DE ENTREGA + TENDENCIA"),
        dbc.Row([
            _chart_card("Funnel de entrega", "ud-gen-funnel-chart", md=5),
            _chart_card("Tendencia multicanal (enviados/dia)", "ud-gen-trend-chart", md=7),
        ], className="mb-4 g-3"),
        _section_label("COMPARACION POR CANAL"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader("Comparacion de canales", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                }),
                dbc.CardBody(dcc.Loading(_data_table("ud-gen-channel-table"))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
    ])


# ===================== Tab 2: WhatsApp (4 sub-tabs) =====================

def _build_whatsapp_tab():
    return dbc.Tab(label="WhatsApp", tab_id="tab-wa", children=[
        dbc.Tabs(
            id="ud-wa-subtabs",
            active_tab="wa-sub-bot",
            className="ud-wa-subtabs mt-2",
            children=[
                _build_wa_marketing_subtab(),
                _build_wa_atendimiento_subtab(),
                _build_wa_bot_subtab(),
                _build_wa_humano_subtab(),
            ],
        ),
    ])


def _build_wa_marketing_subtab():
    return dbc.Tab(
        label="Marketing", tab_id="wa-sub-marketing",
        disabled=True,
        children=[
            html.Div([
                dbc.Alert([
                    html.I(className="bi bi-info-circle-fill me-2"),
                    html.Strong("Marketing WhatsApp: "),
                    "Sin datos de campanas marketing disponibles. ",
                    "Se activara cuando haya campanas configuradas.",
                ], color="info", className="mt-3"),
            ]),
        ],
    )


def _build_wa_atendimiento_subtab():
    return dbc.Tab(label="Atendimiento", tab_id="wa-sub-atend", children=[
        _section_label("RESUMEN DE ATENDIMIENTO"),
        dbc.Row(id="ud-wa-atend-kpi-row", className="mb-4 g-3"),
        _section_label("CLASIFICACION DE CONVERSACIONES"),
        dbc.Row([
            _chart_card("Tipo de conversacion", "ud-wa-atend-type-pie", md=4),
            _chart_card("Tendencia por tipo", "ud-wa-atend-type-trend", md=5),
            _chart_card("Tasa de escalacion", "ud-wa-atend-escalation-gauge", md=3),
        ], className="mb-4 g-3"),
    ])


def _build_wa_bot_subtab():
    """Bot sub-tab: preserves all existing ud-wa-* IDs."""
    return dbc.Tab(label="Bot", tab_id="wa-sub-bot", children=[
        _section_label("RESUMEN WHATSAPP / BOT"),
        dbc.Row(id="ud-wa-kpi-row", className="mb-4 g-3"),
        _section_label("TENDENCIA DE MENSAJES"),
        dbc.Row([
            _chart_card("Mensajes por dia", "ud-wa-messages-trend-chart", md=8),
            _chart_card("Distribucion por direccion", "ud-wa-direction-pie-chart", md=4),
        ], className="mb-4 g-3"),
        _section_label("AUTOMATIZACION Y FALLBACK"),
        dbc.Row([
            _chart_card("Tendencia de fallback (meta 15%)", "ud-wa-fallback-trend-chart", md=8),
            _chart_card("Bot vs Agente", "ud-wa-bot-vs-human-chart", md=4),
        ], className="mb-4 g-3"),
        _section_label("INTENCIONES Y CONTENIDO"),
        dbc.Row([
            _chart_card("Top 10 intenciones", "ud-wa-top-intents-chart", md=6),
            _chart_card("Estado de entrega", "ud-wa-status-chart", md=3),
            _chart_card("Tipos de contenido", "ud-wa-content-type-chart", md=3),
        ], className="mb-4 g-3"),
        _section_label("MAPA DE CALOR"),
        dbc.Row([
            _chart_card("Actividad por hora y dia", "ud-wa-heatmap-chart", md=12),
        ], className="mb-4 g-3"),
        _section_label("DETALLE DE MENSAJES"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Mensajes recientes", style={"fontWeight": "600"}),
                    _csv_button("ud-wa-export-csv-btn"),
                ], style={"backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                           "padding": "14px 20px"}),
                dbc.CardBody(dcc.Loading(_data_table(
                    "ud-wa-detail-table", page_size=15, filterable=True,
                ))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
        dcc.Download(id="ud-wa-download-csv"),
    ])


def _build_wa_humano_subtab():
    """Humano sub-tab: uses contact center data for human agent analysis."""
    return dbc.Tab(label="Humano", tab_id="wa-sub-humano", children=[
        _section_label("RESUMEN AGENTES HUMANOS"),
        dbc.Row(id="ud-wa-hum-kpi-row", className="mb-4 g-3"),
        _section_label("TIEMPOS DE RESPUESTA"),
        dbc.Row([
            _chart_card("FRT - Primer respuesta (meta 1 min)", "ud-wa-hum-frt-trend"),
            _chart_card("Tiempo de gestion (meta 5 min)", "ud-wa-hum-handle-trend"),
        ], className="mb-4 g-3"),
        _section_label("VOLUMEN Y CIERRE"),
        dbc.Row([
            _chart_card("Conversaciones por dia", "ud-wa-hum-conv-trend"),
            _chart_card("Razones de cierre", "ud-wa-hum-close-reasons"),
        ], className="mb-4 g-3"),
        _section_label("DEAD TIME Y COBERTURA"),
        dbc.Row([
            _chart_card("Tiempo muerto promedio", "ud-wa-hum-dead-time"),
            _chart_card("Cobertura contactos", "ud-wa-hum-coverage-pie"),
        ], className="mb-4 g-3"),
        _section_label("DISTRIBUCION HORARIA"),
        dbc.Row([
            _chart_card("Conversaciones por hora", "ud-wa-hum-heatmap", md=12),
        ], className="mb-4 g-3"),
        _section_label("AGENTES"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Rendimiento por agente", style={"fontWeight": "600"}),
                    _csv_button("ud-wa-hum-export-csv-btn"),
                ], style={"backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                           "padding": "14px 20px"}),
                dbc.CardBody(dcc.Loading(_data_table(
                    "ud-wa-hum-agent-table", page_size=15,
                ))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
        dcc.Download(id="ud-wa-hum-download-csv"),
    ])


# ===================== Tab 3: SMS =====================

def _build_sms_tab():
    return dbc.Tab(label="SMS", tab_id="tab-sms", children=[
        _section_label("RESUMEN SMS"),
        dbc.Row(id="ud-sms-kpi-row", className="mb-4 g-3"),
        _section_label("TENDENCIA DE ENVIOS"),
        dbc.Row([
            _chart_card("Enviados vs Chunks por dia", "ud-sms-sends-chunks-chart"),
            _chart_card("Enviados vs Clicks vs CTR", "ud-sms-sends-clicks-chart"),
        ], className="mb-4 g-3"),
        _section_label("PATRONES Y RANKING"),
        dbc.Row([
            _chart_card("Mapa de calor (hora / dia)", "ud-sms-heatmap-chart"),
            _chart_card("Ranking campanas por volumen", "ud-sms-ranking-chart"),
        ], className="mb-4 g-3"),
        _section_label("RANKING POR CTR"),
        dbc.Row([
            _chart_card("Top campanas por CTR (min 100 envios)", "ud-sms-ranking-ctr-chart", md=12),
        ], className="mb-4 g-3"),
        _section_label("ENTREGA Y ESTADO"),
        dbc.Row([
            _chart_card("Tendencia de entrega diaria", "ud-sms-delivery-trend-chart"),
            _chart_card("Estado de envio", "ud-sms-error-pie-chart"),
        ], className="mb-4 g-3"),
        _section_label("TIPO Y RED OPERADORA"),
        dbc.Row([
            _chart_card("Tipo de envio", "ud-sms-type-chart"),
            _chart_card("Distribucion por operadora", "ud-sms-network-chart"),
        ], className="mb-4 g-3"),
        _section_label("DETALLE SMS"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    html.Span(id="ud-sms-detail-total", className="text-muted",
                              style={"fontSize": "13px"}),
                    _csv_button("ud-sms-export-csv-btn"),
                ], style={"backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                           "padding": "14px 20px"}),
                dbc.CardBody(dcc.Loading(_data_table(
                    "ud-sms-detail-table", page_size=15, filterable=True,
                ))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
        dcc.Download(id="ud-sms-download-csv"),
        _section_label("DRILL-DOWN TEMPORAL"),
        dcc.Store(id="ud-sms-drill-store", data={"level": "day"}),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader("Desglose por periodo", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                }),
                dbc.CardBody(html.Div(id="ud-sms-drill-container")),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
    ])


# ===================== Tab 4: Control de Toques (Ley 2300) =====================

def _build_toques_tab():
    return dbc.Tab(label="Control de Toques", tab_id="tab-toques", children=[
        _section_label("CONTROL DE TOQUES — LEY 2300"),
        dbc.Alert([
            html.I(className="bi bi-shield-check me-2"),
            html.Strong("Ley 2300 de 2023: "),
            "Control de frecuencia de contactos por canal y usuario.",
        ], color="info", className="mb-3"),
        dbc.Row(id="ud-toques-kpi-row", className="mb-4 g-3"),
        _section_label("DISTRIBUCION HORARIA DE ENVIOS SMS"),
        dbc.Row([
            _chart_card("Envios por hora del dia", "ud-toques-hour-chart", md=12),
        ], className="mb-4 g-3"),
        _section_label("CONTROL DE USUARIOS MULTICANAL"),
        dbc.Row([
            dbc.Col([
                html.Label("Umbral de toques:", className="me-2",
                           style={"fontSize": "13px", "fontWeight": "500"}),
                dcc.Slider(
                    id="ud-users-threshold", min=1, max=20, step=1, value=4,
                    marks={1: "1", 4: "4", 10: "10", 20: "20"},
                ),
            ], md=6),
        ], className="mb-3"),
        dbc.Row(id="ud-users-kpi-row", className="mb-4 g-3"),
        _section_label("USUARIOS SOBRE-TOCADOS"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    html.Span("Usuarios con alto volumen de toques",
                              style={"fontWeight": "600"}),
                    _csv_button("ud-users-export-csv-btn"),
                ], style={"backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                           "padding": "14px 20px"}),
                dbc.CardBody(dcc.Loading(_data_table(
                    "ud-users-table", page_size=15, filterable=True,
                ))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
        dcc.Download(id="ud-users-download-csv"),
    ])


# ===================== Tab 5: Email (disabled) =====================

def _build_email_tab():
    return dbc.Tab(label="Email", tab_id="tab-email", disabled=True, children=[
        _disabled_tab_content("bi-envelope", "Email"),
        dbc.Row(id="ud-email-kpi-row", className="mb-4 g-3", style={"display": "none"}),
        html.Div([
            dcc.Graph(id="ud-email-engagement-chart", style={"display": "none"}),
            dcc.Graph(id="ud-email-errors-chart", style={"display": "none"}),
            dcc.Graph(id="ud-email-heatmap-chart", style={"display": "none"}),
            dcc.Graph(id="ud-email-ranking-chart", style={"display": "none"}),
        ], style={"display": "none"}),
    ])


# ===================== Tab 6: Push (disabled) =====================

def _build_push_tab():
    return dbc.Tab(label="Push", tab_id="tab-push", disabled=True, children=[
        _disabled_tab_content("bi-bell", "Push"),
        dbc.Row(id="ud-push-kpi-row", className="mb-4 g-3", style={"display": "none"}),
        html.Div([
            dcc.Graph(id="ud-push-trend-chart", style={"display": "none"}),
            dcc.Graph(id="ud-push-heatmap-chart", style={"display": "none"}),
        ], style={"display": "none"}),
    ])


# ===================== Tab 7: In App/Web (disabled) =====================

def _build_inapp_tab():
    return dbc.Tab(label="In App/Web", tab_id="tab-inapp", disabled=True, children=[
        _disabled_tab_content("bi-phone", "In App/Web"),
        dbc.Row(id="ud-inapp-kpi-row", className="mb-4 g-3", style={"display": "none"}),
        html.Div([
            dcc.Graph(id="ud-inapp-engagement-chart", style={"display": "none"}),
            dcc.Graph(id="ud-inapp-funnel-chart", style={"display": "none"}),
        ], style={"display": "none"}),
    ])


# ===================== Tab 8: Contact Center =====================

def _build_cc_tab():
    return dbc.Tab(label="Contact Center", tab_id="tab-cc", children=[
        _section_label("RESUMEN CONTACT CENTER"),
        dbc.Row(id="ud-cc-kpi-row", className="mb-4 g-3"),
        _section_label("VOLUMEN DE CONVERSACIONES"),
        dbc.Row([
            _chart_card("Conversaciones por dia", "ud-cc-conv-trend-chart", md=8),
            _chart_card("Distribucion de espera", "ud-cc-wait-chart", md=4),
        ], className="mb-4 g-3"),
        _section_label("TIEMPOS DE RESPUESTA"),
        dbc.Row([
            _chart_card("Tendencia FRT (primer respuesta)", "ud-cc-frt-trend-chart"),
            _chart_card("Tendencia tiempo de gestion", "ud-cc-handle-trend-chart"),
        ], className="mb-4 g-3"),
        _section_label("RAZONES DE CIERRE"),
        dbc.Row([
            _chart_card("Razones de cierre", "ud-cc-close-reasons-chart"),
            _chart_card("NPS", "ud-cc-nps-chart"),
        ], className="mb-4 g-3"),
        _section_label("AGENTES"),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader("Rendimiento por agente", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                }),
                dbc.CardBody(dcc.Loading(_data_table("ud-cc-agent-table"))),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4 g-3"),
        _section_label("DISTRIBUCION HORARIA"),
        dbc.Row([
            _chart_card("Conversaciones por hora", "ud-cc-hourly-chart", md=12),
        ], className="mb-4"),
        _section_label("DRILL-DOWN"),
        dcc.Store(id="ud-cc-drill-store", data={"level": "month"}),
        dbc.Row([dbc.Col(
            dbc.Card([
                dbc.CardHeader("Desglose por periodo", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "backgroundColor": "transparent", "borderBottom": "1px solid #F0F0F5",
                }),
                dbc.CardBody(html.Div(id="ud-cc-drill-container")),
            ], style={"borderRadius": "16px", "border": "1px solid #F0F0F5",
                       "boxShadow": "0 2px 12px rgba(0,0,0,0.04)"}),
            md=12,
        )], className="mb-4"),
    ])


# ===================== Tab 9: Wallet (disabled) =====================

def _build_wallet_tab():
    return dbc.Tab(label="Wallet", tab_id="tab-wallet", disabled=True, children=[
        _disabled_tab_content("bi-wallet2", "Wallet"),
    ])


# ===================== Main Layout =====================

layout = dbc.Container([
    dcc.Store(id="ud-view-store", storage_type="session", data="gallery"),
    _build_gallery(),
    _build_dashboard(),
], fluid=True, className="py-4")
