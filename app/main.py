"""
inDigitall BI Platform — Main Dash Application

Redash-inspired analytics platform with AI assistant.
Top navbar navigation, multi-page layout with dash.page_container.
"""

import dash
from dash import html, dcc, page_container
import dash_bootstrap_components as dbc

from app.config import settings

# --- Sentry (optional) ---
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FlaskIntegration()])

# --- Dash App ---
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="layouts",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
    title="inDigitall Analytics",
    update_title="Cargando...",
)

server = app.server
server.secret_key = settings.FLASK_SECRET_KEY

# --- Auth middleware ---
from app.middleware.auth import init_auth
init_auth(server, settings)


# --- Health check endpoint ---
@server.route("/health")
def health():
    return {"status": "ok", "auth_mode": settings.AUTH_MODE}


# --- Navbar ---
def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                # Left: Logo + Brand
                dbc.NavbarBrand(
                    html.Div([
                        html.Img(
                            src=app.get_asset_url("indigitall_logo.webp"),
                            height="32px",
                            className="me-2",
                        ),
                        html.Span("Analytics", className="brand-text"),
                    ], className="d-flex align-items-center"),
                    href="/",
                    className="navbar-brand-custom",
                ),
                # Center: Navigation links
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink(
                            [html.I(className="bi bi-house-door me-1"), "Inicio"],
                            href="/", active="exact",
                        )),
                        dbc.NavItem(dbc.NavLink(
                            [html.I(className="bi bi-search me-1"), "Consultas"],
                            href="/consultas", active="exact",
                        )),
                        dbc.NavItem(dbc.NavLink(
                            [html.I(className="bi bi-grid-1x2 me-1"), "Tableros"],
                            href="/tableros", active="exact",
                        )),
                    ],
                    className="mx-auto",
                    navbar=True,
                ),
                # Right: Create button + Tenant selector
                html.Div([
                    dbc.DropdownMenu(
                        label=[html.I(className="bi bi-plus-lg me-1"), "Crear"],
                        children=[
                            dbc.DropdownMenuItem(
                                [html.I(className="bi bi-chat-dots me-2"), "Nueva Consulta"],
                                href="/consultas/nueva",
                            ),
                            dbc.DropdownMenuItem(
                                [html.I(className="bi bi-grid-1x2 me-2"), "Nuevo Tablero"],
                                href="/tableros/nuevo",
                            ),
                        ],
                        nav=True,
                        in_navbar=True,
                        className="create-dropdown me-3",
                        toggle_class_name="btn btn-sm btn-primary",
                    ),
                    dcc.Dropdown(
                        id="tenant-selector",
                        placeholder="Proyecto...",
                        className="tenant-dropdown",
                        style={"width": "200px"},
                    ),
                ], className="d-flex align-items-center"),
            ],
            fluid=True,
        ),
        color="white",
        dark=False,
        className="navbar-indigitall",
        sticky="top",
    )


# --- Layout ---
app.layout = html.Div([
    # Global stores
    dcc.Store(id="chat-history", storage_type="session"),
    dcc.Store(id="query-result", storage_type="memory"),
    dcc.Store(id="dashboard-layout", storage_type="memory"),
    dcc.Store(id="user-preferences", storage_type="local"),
    dcc.Store(id="active-filters", storage_type="session"),
    dcc.Store(id="tenant-context", storage_type="session", data=settings.DEFAULT_TENANT),
    dcc.Location(id="url", refresh="callback-nav"),

    # Top navbar
    create_navbar(),

    # Page content
    html.Div(
        page_container,
        className="page-content",
    ),

    # Toast notifications container
    html.Div(id="toast-container"),
])


# --- Register callbacks ---
# Importing callback modules triggers @callback registration with Dash.
import app.callbacks.nav_cb  # noqa: F401
import app.callbacks.home_cb  # noqa: F401
import app.callbacks.query_cb  # noqa: F401
import app.callbacks.query_list_cb  # noqa: F401
import app.callbacks.dashboard_list_cb  # noqa: F401
import app.callbacks.dashboard_view_cb  # noqa: F401


if __name__ == "__main__":
    app.run(debug=settings.DEBUG, port=8050)
