"""
Phase 1 — JSONB Quality Analysis: key catalog, duplicates, types, fill rates, field mapping.

Usage:
    docker compose exec app python scripts/analyze_raw_quality.py
    python scripts/analyze_raw_quality.py          # local (requires .env)
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine

# ---------------------------------------------------------------------------
# Target mapping: raw JSON field → public column → SQL type
# ---------------------------------------------------------------------------

FIELD_MAPPING = {
    "raw_contacts_api": {
        "source_endpoint": "/v1/chat/contacts",
        "maps_to": "public.contacts",
        "fields": {
            "contactId":        ("contact_id",    "VARCHAR(100)"),
            "profileName":      ("contact_name",  "VARCHAR(255)"),
            "createdAt":        ("first_contact",  "DATE"),
            "updatedAt":        ("last_contact",   "DATE"),
            "channel":          ("—",              "info only"),
            "instanceId":       ("—",              "info only"),
            "chatAllowed":      ("—",              "info only"),
            "agentId":          ("—",              "info only"),
            "lastInputMessage": ("—",              "info only"),
        },
    },
    "raw_push_stats (dateStats)": {
        "source_endpoint": "/v1/application/{id}/dateStats",
        "maps_to": "public.toques_daily",
        "fields": {
            "platformGroup":    ("canal",          "VARCHAR(30)"),
            "statsDate":        ("date",           "DATE"),
            "numDevicesSent":   ("enviados",       "INTEGER"),
            "numDevicesSuccess":("entregados",     "INTEGER"),
            "numDevicesReceived":("abiertos",      "INTEGER"),
            "numDevicesClicked":("clicks",         "INTEGER"),
        },
    },
    "raw_push_stats (pushHeatmap)": {
        "source_endpoint": "/v1/application/{id}/pushHeatmap",
        "maps_to": "public.toques_heatmap",
        "fields": {
            "weekday-hour.{weekday}.{hour}": ("dia_semana + hora", "engagement rate"),
        },
    },
    "raw_campaigns_api": {
        "source_endpoint": "/v1/campaign",
        "maps_to": "public.campaigns",
        "fields": {
            "id":              ("campana_id",      "VARCHAR(100)"),
            "name":            ("campana_nombre",  "VARCHAR(255)"),
            "channel":         ("canal",           "VARCHAR(30)"),
            "status":          ("tipo_campana",    "VARCHAR(50)"),
        },
    },
    "raw_chat_stats (agent/status)": {
        "source_endpoint": "/v1/chat/agent/status",
        "maps_to": "public.agents (minimal)",
        "fields": {
            "activeAgents": ("agent count", "INTEGER"),
        },
    },
}

# Tables with array-type data to analyze
ARRAY_TABLES = [
    ("raw.raw_contacts_api", "/v1/chat/contacts"),
    ("raw.raw_push_stats", None),  # multiple endpoints
    ("raw.raw_campaigns_api", "/v1/campaign"),
]


def analyze_duplicates(conn, table: str, endpoint_filter: str | None = None):
    """Check for duplicate records (same endpoint + date_from + date_to)."""
    where = ""
    params = {}
    if endpoint_filter:
        where = "WHERE endpoint = :ep"
        params = {"ep": endpoint_filter}

    rows = conn.execute(text(f"""
        SELECT endpoint, date_from, date_to, count(*) AS cnt
        FROM {table}
        {where}
        GROUP BY endpoint, date_from, date_to
        HAVING count(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
    """), params).fetchall()

    if rows:
        print(f"    Duplicates found ({len(rows)} groups):")
        for r in rows:
            print(f"      {r[0]}  {r[1]} → {r[2]}  ×{r[3]}")
    else:
        print(f"    No duplicate (endpoint, date_from, date_to) groups")


def analyze_array_fill_rates(conn, table: str, endpoint_filter: str | None = None):
    """For tables where source_data->'data' is an array, compute per-field fill rates."""
    where = ""
    params = {}
    if endpoint_filter:
        where = "WHERE endpoint = :ep"
        params = {"ep": endpoint_filter}

    # Check if data is an array
    dtype_row = conn.execute(text(f"""
        SELECT jsonb_typeof(source_data->'data') AS dtype
        FROM {table}
        {where}
        LIMIT 1
    """), params).fetchone()

    if not dtype_row:
        print(f"    (no rows)")
        return

    if dtype_row[0] != "array":
        print(f"    data type: {dtype_row[0]} (not array — skipping element fill rates)")
        return

    # Get total element count
    total_row = conn.execute(text(f"""
        SELECT count(*) AS total_elems
        FROM {table} t, jsonb_array_elements(t.source_data->'data') AS elem
        {where.replace('endpoint', 't.endpoint') if where else ''}
    """), params).fetchone()
    total = total_row[0]
    print(f"    Total array elements: {total}")

    if total == 0:
        return

    # Get all keys
    keys = [r[0] for r in conn.execute(text(f"""
        SELECT DISTINCT k
        FROM {table} t, jsonb_array_elements(t.source_data->'data') AS elem,
             jsonb_object_keys(elem) AS k
        {where.replace('endpoint', 't.endpoint') if where else ''}
        ORDER BY k
    """), params).fetchall()]

    # Fill rate per key
    print(f"    Field fill rates ({total} elements):")
    for key in keys:
        non_null = conn.execute(text(f"""
            SELECT count(*) FROM (
                SELECT elem->>:key AS val
                FROM {table} t, jsonb_array_elements(t.source_data->'data') AS elem
                {where.replace('endpoint', 't.endpoint') if where else ''}
            ) sub
            WHERE val IS NOT NULL AND val != 'null' AND val != ''
        """), {**params, "key": key}).fetchone()[0]
        pct = (non_null / total * 100) if total > 0 else 0
        print(f"      {key:<25s}  {non_null:>5d}/{total}  ({pct:5.1f}%)")


def analyze_timestamp_validity(conn, table: str, field: str, endpoint_filter: str | None = None):
    """Check if ISO timestamp fields parse correctly."""
    where = ""
    params = {}
    if endpoint_filter:
        where = "WHERE t.endpoint = :ep"
        params = {"ep": endpoint_filter}

    bad = conn.execute(text(f"""
        SELECT count(*) FROM (
            SELECT elem->>:field AS ts
            FROM {table} t, jsonb_array_elements(t.source_data->'data') AS elem
            {where}
        ) sub
        WHERE ts IS NOT NULL
          AND ts != 'null'
          AND ts !~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}'
    """), {**params, "field": field}).fetchone()[0]

    if bad > 0:
        print(f"    [WARN] {field}: {bad} values don't match ISO 8601 pattern")
    else:
        print(f"    {field}: all values match ISO 8601 pattern")


def main():
    print("=" * 60)
    print("  JSONB Quality Analysis — Phase 1")
    print("=" * 60)

    with engine.connect() as conn:
        # ---- raw_contacts_api ----
        print(f"\n{'─' * 60}")
        print("  raw.raw_contacts_api  →  public.contacts")
        print(f"{'─' * 60}")
        analyze_duplicates(conn, "raw.raw_contacts_api")
        analyze_array_fill_rates(conn, "raw.raw_contacts_api")
        try:
            analyze_timestamp_validity(conn, "raw.raw_contacts_api", "createdAt")
            analyze_timestamp_validity(conn, "raw.raw_contacts_api", "updatedAt")
        except Exception as exc:
            print(f"    [SKIP] Timestamp check: {exc}")

        # ---- raw_push_stats (dateStats) ----
        print(f"\n{'─' * 60}")
        print("  raw.raw_push_stats (dateStats)  →  public.toques_daily")
        print(f"{'─' * 60}")
        analyze_duplicates(conn, "raw.raw_push_stats", endpoint_filter=None)
        # Get distinct endpoints
        eps = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT endpoint FROM raw.raw_push_stats ORDER BY endpoint"
        )).fetchall()]
        for ep in eps:
            print(f"\n    Endpoint: {ep}")
            analyze_array_fill_rates(conn, "raw.raw_push_stats", endpoint_filter=ep)

        # ---- raw_campaigns_api ----
        print(f"\n{'─' * 60}")
        print("  raw.raw_campaigns_api  →  public.campaigns")
        print(f"{'─' * 60}")
        analyze_duplicates(conn, "raw.raw_campaigns_api")
        analyze_array_fill_rates(conn, "raw.raw_campaigns_api")

        # ---- raw_chat_stats ----
        print(f"\n{'─' * 60}")
        print("  raw.raw_chat_stats  →  public.agents (minimal)")
        print(f"{'─' * 60}")
        analyze_duplicates(conn, "raw.raw_chat_stats")
        eps = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT endpoint FROM raw.raw_chat_stats ORDER BY endpoint"
        )).fetchall()]
        for ep in eps:
            print(f"\n    Endpoint: {ep}")
            dtype = conn.execute(text("""
                SELECT jsonb_typeof(source_data->'data') FROM raw.raw_chat_stats
                WHERE endpoint = :ep LIMIT 1
            """), {"ep": ep}).fetchone()
            if dtype:
                print(f"    data type: {dtype[0]}")

        # ---- raw_applications ----
        print(f"\n{'─' * 60}")
        print("  raw.raw_applications")
        print(f"{'─' * 60}")
        analyze_duplicates(conn, "raw.raw_applications")
        analyze_array_fill_rates(conn, "raw.raw_applications")

        # ---- Field mapping report ----
        print(f"\n{'=' * 60}")
        print("  FIELD MAPPING REPORT")
        print(f"{'=' * 60}")
        for source, info in FIELD_MAPPING.items():
            print(f"\n  {source}")
            print(f"    endpoint : {info['source_endpoint']}")
            print(f"    target   : {info['maps_to']}")
            print(f"    {'Raw Field':<30s}  {'Public Column':<20s}  {'Type'}")
            print(f"    {'─' * 30}  {'─' * 20}  {'─' * 15}")
            for raw_field, (pub_col, sql_type) in info["fields"].items():
                print(f"    {raw_field:<30s}  {pub_col:<20s}  {sql_type}")

    print(f"\n{'=' * 60}")
    print("  Quality analysis complete.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
