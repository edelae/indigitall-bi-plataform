"""Discover Indigitall applications and identify Visionamos projects."""

import json

from sqlalchemy import text

from scripts.extractors.api_client import IndigitallAPIClient

# Keywords that identify Visionamos cooperatives
VISIONAMOS_KEYWORDS = [
    "cooprofesionales",
    "coovimag",
    "utrahuilca",
    "cooprudea",
    "vidasol",
    "visionamos",
]


def discover_applications(client: IndigitallAPIClient, engine) -> list[dict]:
    """GET /v1/application — list all applications the account can see.

    The am1 API requires ?limit=<n>&page=<n> query params.
    """
    print("\n--- Application Discovery ---")
    data = client.get("/v1/application", params={"limit": 100, "page": 0})

    if not data:
        print("  [WARN] No applications returned from /v1/application")
        return []

    # The response is: {"statusCode":200, "message":"OK", "count":N, "data":[...]}
    apps = data if isinstance(data, list) else data.get("data", data.get("applications", []))
    if isinstance(apps, dict):
        apps = [apps]

    # Store raw discovery result
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO raw.raw_applications
                        (application_id, endpoint, source_data)
                    VALUES
                        (:app_id, :endpoint, :data)
                """),
                {
                    "app_id": "discovery",
                    "endpoint": "/v1/application",
                    "data": json.dumps(data) if not isinstance(data, str) else data,
                },
            )
    except Exception as exc:
        print(f"  [WARN] Could not store discovery data: {exc}")

    print(f"  Found {len(apps)} application(s):")
    for app in apps:
        name = app.get("name", "?")
        app_id = app.get("id", app.get("appKey", "?"))
        enabled = []
        if app.get("chatEnabled"):
            enabled.append("chat")
        if app.get("androidEnabled") or app.get("iosEnabled") or app.get("webpushEnabled"):
            enabled.append("push")
        print(f"    - {name} (id={app_id}) [{', '.join(enabled) or 'none'}]")

    return apps


def get_visionamos_apps(apps: list[dict]) -> list[dict]:
    """Filter applications that match Visionamos cooperative names."""
    matched = []
    for app in apps:
        name = (app.get("name") or "").lower()
        if any(kw in name for kw in VISIONAMOS_KEYWORDS):
            matched.append(app)

    if matched:
        print(f"\n  Visionamos apps found: {len(matched)}")
        for app in matched:
            print(f"    - {app.get('name')}")
    else:
        print("\n  No Visionamos-specific apps found by keyword match")

    return matched
