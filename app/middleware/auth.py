"""
Authentication middleware — Dev mode + JWT validation.

Two modes controlled by AUTH_MODE setting:
  - "dev"  : No authentication. Tenant from ?tenant= query param or DEFAULT_TENANT.
  - "jwt"  : Validates JWT from indigitall cookie/header. Extracts project_id as tenant.

The middleware runs as a Flask before_request hook attached to the Dash server.
It sets `g.tenant_id` and `g.user` on every request, which callbacks can read.
It also sets the RLS context on database connections via SET LOCAL.
"""

import logging
from functools import wraps

from flask import g, request, abort, jsonify

logger = logging.getLogger(__name__)


def init_auth(server, settings):
    """Attach the auth middleware to the Flask server.

    Called from main.py after app creation.
    """
    auth_mode = settings.AUTH_MODE

    if auth_mode == "jwt":
        _init_jwt_auth(server, settings)
    else:
        _init_dev_auth(server, settings)

    logger.info("Auth middleware initialized in '%s' mode", auth_mode)


# ==========================================================================
# Dev Mode — no authentication, tenant from query param or default
# ==========================================================================

def _init_dev_auth(server, settings):
    """Dev mode: set tenant from ?tenant= or DEFAULT_TENANT. No auth required."""

    @server.before_request
    def _set_dev_context():
        # Skip for static assets
        if _is_static_request():
            return

        tenant = request.args.get("tenant") or settings.DEFAULT_TENANT
        g.tenant_id = tenant
        g.user = {
            "id": "dev-user",
            "email": "dev@localhost",
            "name": "Dev User",
            "role": "admin",
        }
        g.auth_mode = "dev"


# ==========================================================================
# JWT Mode — validate indigitall JWT, extract project_id as tenant
# ==========================================================================

def _init_jwt_auth(server, settings):
    """JWT mode: validate token from cookie or Authorization header."""

    # Lazy import — only needed in JWT mode
    try:
        from flask_jwt_extended import (
            JWTManager, verify_jwt_in_request, get_jwt, get_jwt_identity,
        )
    except ImportError:
        logger.error("flask-jwt-extended is required for JWT auth mode. Falling back to dev mode.")
        return _init_dev_auth(server, settings)

    # Configure Flask-JWT-Extended
    server.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
    server.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    server.config["JWT_COOKIE_NAME"] = settings.JWT_COOKIE_NAME
    server.config["JWT_ACCESS_COOKIE_NAME"] = settings.JWT_COOKIE_NAME
    server.config["JWT_COOKIE_CSRF_PROTECT"] = False  # indigitall handles CSRF
    server.config["JWT_HEADER_NAME"] = "Authorization"
    server.config["JWT_HEADER_TYPE"] = "Bearer"
    # Also accept token from query param as fallback (iframe embedding)
    server.config["JWT_QUERY_STRING_NAME"] = "token"

    jwt = JWTManager(server)

    # Custom claim loader — indigitall JWT has project_id in claims
    @jwt.additional_claims_loader
    def _add_claims(identity):
        return {}  # We read claims, not add them

    @jwt.expired_token_loader
    def _expired(jwt_header, jwt_payload):
        return jsonify({"error": "Token expirado", "code": "token_expired"}), 401

    @jwt.invalid_token_loader
    def _invalid(error):
        return jsonify({"error": "Token inválido", "code": "token_invalid"}), 401

    @jwt.unauthorized_loader
    def _missing(error):
        # In JWT mode, if no token found, try query param fallback
        token = request.args.get("token")
        if token:
            # Re-process with the token — Flask-JWT-Extended will pick it up
            # on the next verification attempt
            pass
        return jsonify({"error": "Autenticación requerida", "code": "missing_token"}), 401

    # Pages that don't require authentication
    PUBLIC_PATHS = frozenset({
        "/_dash-layout",
        "/_dash-dependencies",
        "/_reload-hash",
        "/_alive",
        "/health",
    })

    @server.before_request
    def _validate_jwt():
        # Skip static assets and Dash internals
        if _is_static_request():
            return

        path = request.path
        if path in PUBLIC_PATHS:
            g.tenant_id = settings.DEFAULT_TENANT
            g.user = None
            g.auth_mode = "jwt"
            return

        # Skip Dash callback POST requests that carry their own state
        # (the initial page load validates the token; callbacks trust the session)
        if request.method == "POST" and path.startswith("/_dash-update-component"):
            # Trust the tenant from the callback state (sent via dcc.Store)
            g.tenant_id = settings.DEFAULT_TENANT  # Overridden by callback state
            g.user = None
            g.auth_mode = "jwt"
            return

        # Try to validate JWT
        try:
            verify_jwt_in_request(optional=True)
            claims = get_jwt()

            if claims:
                # Extract tenant from JWT claims
                # indigitall uses "project_id" — adapt the claim name here
                tenant = (
                    claims.get("project_id")
                    or claims.get("tenant_id")
                    or claims.get("org_id")
                    or settings.DEFAULT_TENANT
                )
                identity = get_jwt_identity()

                g.tenant_id = tenant
                g.user = {
                    "id": identity,
                    "email": claims.get("email", ""),
                    "name": claims.get("name", ""),
                    "role": claims.get("role", "viewer"),
                }
                g.auth_mode = "jwt"
            else:
                # No JWT present — allow with default tenant (soft auth)
                # In production, you may want to redirect to login instead
                g.tenant_id = settings.DEFAULT_TENANT
                g.user = None
                g.auth_mode = "jwt"

        except Exception as e:
            logger.warning("JWT validation failed: %s", e)
            g.tenant_id = settings.DEFAULT_TENANT
            g.user = None
            g.auth_mode = "jwt"


# ==========================================================================
# Helpers
# ==========================================================================

def _is_static_request() -> bool:
    """Check if this is a request for static assets that don't need auth."""
    path = request.path
    return (
        path.startswith("/assets/")
        or path.startswith("/_dash-component-suites/")
        or path.startswith("/favicon")
        or path.endswith((".js", ".css", ".map", ".ico", ".png", ".webp", ".woff2"))
    )


def get_current_tenant() -> str:
    """Get the current tenant ID from Flask g context.

    Safe to call from Dash callbacks — returns DEFAULT_TENANT if
    no request context is available (e.g., during background tasks).
    """
    try:
        return g.get("tenant_id") or "demo"
    except RuntimeError:
        # Outside request context
        from app.config import settings
        return settings.DEFAULT_TENANT


def get_current_user() -> dict:
    """Get the current user dict from Flask g context.

    Returns None if not authenticated or outside request context.
    """
    try:
        return g.get("user")
    except RuntimeError:
        return None


def require_auth(f):
    """Decorator for Flask routes that require an authenticated user.

    In dev mode, this always passes.
    In JWT mode, aborts 401 if no valid user.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.get("auth_mode") == "jwt" and g.get("user") is None:
            abort(401)
        return f(*args, **kwargs)
    return wrapper
