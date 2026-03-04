"""
inDigitall BI Platform — Main Dash Application

Redash-inspired analytics platform with AI assistant.
Top navbar navigation, multi-page layout with dash.page_container.
"""

import dash
from dash import html, dcc, page_container
import dash_bootstrap_components as dbc

import threading
from datetime import datetime, timezone
from flask import request, jsonify

from app.config import settings
from app.logging_config import setup_logging

# --- Logging ---
setup_logging()

import logging as _logging
_startup_logger = _logging.getLogger("app.startup")
_startup_logger.info(
    "AI keys loaded — OpenAI: %s, Anthropic: %s",
    "YES" if settings.has_openai_key else "NO",
    "YES" if settings.has_ai_key else "NO",
)

# --- Sentry (optional) ---
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FlaskIntegration()])

# --- Dash App ---
# Named `dash_app` to avoid shadowing the `app` package name.
dash_app = dash.Dash(
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
        {"charset": "utf-8"},
    ],
    title="inDigitall Analytics",
    update_title="Cargando...",
)

server = dash_app.server
server.secret_key = settings.FLASK_SECRET_KEY
server.config["JSON_AS_ASCII"] = False  # Serve JSON with native UTF-8 chars

# --- Auth middleware ---
from app.middleware.auth import init_auth
init_auth(server, settings)


# --- Health check endpoint ---
@server.route("/health")
def health():
    return {"status": "ok", "auth_mode": settings.AUTH_MODE}


# --- Pipeline API (for n8n / cron automation) ---

_pipeline_state = {
    "running": False,
    "last_run": None,
    "last_status": None,
    "last_duration_s": None,
    "last_results": None,
}
_pipeline_lock = threading.Lock()


def _run_pipeline_background(skip_extract=False, skip_dbt=False):
    """Execute the ETL pipeline in a background thread."""
    import time
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    start = time.time()
    results = {}
    errors = []

    try:
        # Step 1: Extract (API → raw.*)
        if not skip_extract:
            try:
                from scripts.extractors.orchestrator import main as extraction_main
                extraction_main()
                results["extract"] = "ok"
            except Exception as exc:
                results["extract"] = f"error: {str(exc)[:200]}"
                errors.append(f"extract: {exc}")

        # Step 2: Transform (raw.* → public.*)
        try:
            from scripts.transform_bridge import main as transform_main
            rc = transform_main()
            results["transform"] = "ok" if rc == 0 else "error"
        except Exception as exc:
            results["transform"] = f"error: {str(exc)[:200]}"
            errors.append(f"transform: {exc}")

        # Step 3: dbt (optional)
        if not skip_dbt:
            import subprocess
            project_root = Path(__file__).resolve().parent.parent
            dbt_dir = project_root / "dbt"
            try:
                r = subprocess.run(
                    ["dbt", "run"], cwd=str(dbt_dir),
                    capture_output=True, text=True, timeout=120,
                )
                results["dbt_run"] = "ok" if r.returncode == 0 else "error"
            except Exception as exc:
                results["dbt_run"] = f"error: {str(exc)[:100]}"

        elapsed = time.time() - start
        status = "success" if not errors else "partial_error"

    except Exception as exc:
        elapsed = time.time() - start
        status = "error"
        results["fatal"] = str(exc)[:300]

    with _pipeline_lock:
        _pipeline_state["running"] = False
        _pipeline_state["last_run"] = datetime.now(timezone.utc).isoformat()
        _pipeline_state["last_status"] = status
        _pipeline_state["last_duration_s"] = round(elapsed, 1)
        _pipeline_state["last_results"] = results


@server.route("/api/run-pipeline", methods=["POST"])
def api_run_pipeline():
    """Trigger the ETL pipeline. Called by n8n or cron.

    Query params:
        skip_extract=1  — skip API extraction, only transform
        skip_dbt=1      — skip dbt run step
    Returns immediately with 202 Accepted (pipeline runs in background).
    """
    with _pipeline_lock:
        if _pipeline_state["running"]:
            return jsonify({
                "status": "already_running",
                "message": "Pipeline is already running. Check /api/pipeline-status.",
            }), 409

        _pipeline_state["running"] = True

    skip_extract = request.args.get("skip_extract", "0") == "1"
    skip_dbt = request.args.get("skip_dbt", "0") == "1"

    thread = threading.Thread(
        target=_run_pipeline_background,
        args=(skip_extract, skip_dbt),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": "Pipeline started in background.",
        "skip_extract": skip_extract,
        "skip_dbt": skip_dbt,
    }), 202


@server.route("/api/pipeline-status", methods=["GET"])
def api_pipeline_status():
    """Check pipeline execution status."""
    with _pipeline_lock:
        return jsonify(_pipeline_state)


# --- Navbar ---
def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                # Left: Logo + Brand
                dbc.NavbarBrand(
                    html.Div([
                        html.Img(
                            src=dash_app.get_asset_url("indigitall_logo.webp"),
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
                        dbc.NavItem(dbc.NavLink(
                            [html.I(className="bi bi-database me-1"), "Datos"],
                            href="/datos", active="exact",
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
dash_app.layout = html.Div([
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
import app.callbacks.ud_date_cb  # noqa: F401
import app.callbacks.ud_general_cb  # noqa: F401
import app.callbacks.ud_whatsapp_bot_cb  # noqa: F401
import app.callbacks.ud_wa_atendimiento_cb  # noqa: F401
import app.callbacks.ud_wa_humano_cb  # noqa: F401
import app.callbacks.ud_sms_cb  # noqa: F401
import app.callbacks.ud_users_cb  # noqa: F401
import app.callbacks.ud_email_cb  # noqa: F401
import app.callbacks.ud_push_cb  # noqa: F401
import app.callbacks.ud_inapp_cb  # noqa: F401
import app.callbacks.ud_wallet_cb  # noqa: F401
import app.callbacks.ud_gallery_cb  # noqa: F401
import app.callbacks.dashboard_view_cb  # noqa: F401
import app.callbacks.dashboard_builder_cb  # noqa: F401
import app.callbacks.data_explorer_cb  # noqa: F401
import app.callbacks.operations_cb  # noqa: F401


if __name__ == "__main__":
    dash_app.run(debug=settings.DEBUG, port=8050)
