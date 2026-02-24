"""
Phase 0 — Audit raw.* tables: row counts, JSONB keys, date ranges, endpoints.

Usage:
    docker compose exec app python scripts/audit_raw_data.py
    python scripts/audit_raw_data.py          # local (requires .env)
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine

RAW_TABLES = [
    "raw.raw_applications",
    "raw.raw_push_stats",
    "raw.raw_chat_stats",
    "raw.raw_sms_stats",
    "raw.raw_email_stats",
    "raw.raw_inapp_stats",
    "raw.raw_campaigns_api",
    "raw.raw_contacts_api",
    "raw.extraction_log",
]


def audit_table(conn, table: str):
    """Print audit info for a single raw table."""
    print(f"\n{'─' * 60}")
    print(f"  {table}")
    print(f"{'─' * 60}")

    # Row count
    row = conn.execute(text(f"SELECT count(*) AS cnt FROM {table}")).fetchone()
    count = row[0]
    print(f"  Rows: {count}")

    if count == 0:
        print("  (empty — skipping detail)")
        return

    # Date range
    if table != "raw.extraction_log":
        row = conn.execute(text(f"""
            SELECT min(loaded_at)  AS min_loaded,
                   max(loaded_at)  AS max_loaded,
                   min(date_from)  AS min_from,
                   max(date_to)    AS max_to
            FROM {table}
        """)).fetchone()
        print(f"  loaded_at   : {row[0]}  →  {row[1]}")
        print(f"  date range  : {row[2]}  →  {row[3]}")
    else:
        row = conn.execute(text("""
            SELECT min(started_at) AS min_ts, max(started_at) AS max_ts
            FROM raw.extraction_log
        """)).fetchone()
        print(f"  started_at  : {row[0]}  →  {row[1]}")

    # Distinct endpoints
    if table != "raw.extraction_log":
        rows = conn.execute(text(f"""
            SELECT endpoint, count(*) AS cnt
            FROM {table}
            GROUP BY endpoint
            ORDER BY cnt DESC
        """)).fetchall()
        print(f"  Endpoints ({len(rows)}):")
        for r in rows:
            print(f"    {r[0] or '(null)':<50s}  {r[1]:>4d} rows")
    else:
        rows = conn.execute(text("""
            SELECT endpoint, count(*) AS cnt, sum(case when http_status=200 then 1 else 0 end) AS ok
            FROM raw.extraction_log
            GROUP BY endpoint ORDER BY cnt DESC
        """)).fetchall()
        print(f"  Endpoints ({len(rows)}):")
        for r in rows:
            print(f"    {r[0] or '(null)':<50s}  {r[1]:>4d} calls  ({r[2]} ok)")

    # Sample JSONB keys (top-level from source_data)
    if table != "raw.extraction_log":
        row = conn.execute(text(f"""
            SELECT jsonb_object_keys(source_data) AS k
            FROM {table}
            LIMIT 1
        """)).fetchall()
        if row:
            keys = [r[0] for r in conn.execute(text(f"""
                SELECT DISTINCT k
                FROM (
                    SELECT jsonb_object_keys(source_data) AS k
                    FROM {table}
                    LIMIT 50
                ) sub
                ORDER BY k
            """)).fetchall()]
            print(f"  Top-level JSONB keys: {keys}")

        # Keys inside source_data->'data' (if array)
        sample = conn.execute(text(f"""
            SELECT jsonb_typeof(source_data->'data') AS dtype
            FROM {table} LIMIT 1
        """)).fetchone()
        if sample and sample[0] == "array":
            inner_keys = [r[0] for r in conn.execute(text(f"""
                SELECT DISTINCT k
                FROM (
                    SELECT jsonb_object_keys(elem) AS k
                    FROM {table},
                         jsonb_array_elements(source_data->'data') AS elem
                    LIMIT 200
                ) sub
                ORDER BY k
            """)).fetchall()]
            print(f"  data[] element keys : {inner_keys}")
        elif sample and sample[0] == "object":
            inner_keys = [r[0] for r in conn.execute(text(f"""
                SELECT DISTINCT k
                FROM (
                    SELECT jsonb_object_keys(source_data->'data') AS k
                    FROM {table}
                    LIMIT 50
                ) sub
                ORDER BY k
            """)).fetchall()]
            print(f"  data{{}} object keys  : {inner_keys}")

    # NULL analysis for key columns
    if table != "raw.extraction_log":
        null_row = conn.execute(text(f"""
            SELECT
                sum(case when application_id IS NULL then 1 else 0 end) AS null_app,
                sum(case when tenant_id IS NULL then 1 else 0 end) AS null_tenant,
                sum(case when endpoint IS NULL then 1 else 0 end) AS null_ep,
                sum(case when date_from IS NULL then 1 else 0 end) AS null_dfrom,
                sum(case when date_to IS NULL then 1 else 0 end) AS null_dto,
                count(*) AS total
            FROM {table}
        """)).fetchone()
        total = null_row[5]
        nulls = {
            "application_id": null_row[0],
            "tenant_id": null_row[1],
            "endpoint": null_row[2],
            "date_from": null_row[3],
            "date_to": null_row[4],
        }
        always_null = [k for k, v in nulls.items() if v == total]
        if always_null:
            print(f"  Always NULL columns : {always_null}")


def main():
    print("=" * 60)
    print("  Raw Data Audit — Phase 0")
    print("=" * 60)

    with engine.connect() as conn:
        # Check schema exists
        exists = conn.execute(text(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'raw'"
        )).fetchone()
        if not exists:
            print("\n  [ERROR] Schema 'raw' does not exist. Run create_raw_schema.py first.")
            sys.exit(1)

        for table in RAW_TABLES:
            try:
                audit_table(conn, table)
            except Exception as exc:
                print(f"\n  [ERROR] {table}: {exc}")

    print(f"\n{'=' * 60}")
    print("  Audit complete.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
