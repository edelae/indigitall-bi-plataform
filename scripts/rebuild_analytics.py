"""Rebuild analytics star schema — direct SQL (no dbt CLI needed).

Reads dbt .sql files, replaces Jinja refs with schema-qualified names,
and executes in dependency order. Works around dbt CLI incompatibility
with Python 3.14.

Usage:
    python scripts/rebuild_analytics.py              # full rebuild
    python scripts/rebuild_analytics.py --phase B    # only staging views
    python scripts/rebuild_analytics.py --dry-run    # validate without executing
"""
import csv
import os
import re
import sys
import time

import psycopg2
from dotenv import dotenv_values

# ── Config ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBT_DIR = os.path.join(BASE_DIR, "dbt")
MODELS_DIR = os.path.join(DBT_DIR, "models")
SEEDS_DIR = os.path.join(DBT_DIR, "seeds")

env = dotenv_values(os.path.join(BASE_DIR, ".env"))
DB_HOST = env.get("DB_HOST", "localhost")
DB_PASS = env.get("POSTGRES_PASSWORD", "")

# Schema mapping (matches dbt generate_schema_name default)
SCHEMA_MAP = {
    "source": "public",
    "staging": "public_staging",
    "analytics": "public_analytics",
}

# ── CLI args ────────────────────────────────────────────
PHASE_FILTER = None
DRY_RUN = "--dry-run" in sys.argv
for i, arg in enumerate(sys.argv):
    if arg == "--phase" and i + 1 < len(sys.argv):
        PHASE_FILTER = sys.argv[i + 1].upper()


def get_db():
    conn = psycopg2.connect(
        host=DB_HOST, port=5432, dbname="postgres",
        user="postgres", password=DB_PASS,
    )
    conn.autocommit = True
    return conn


def read_sql_file(relative_path):
    """Read a .sql file from dbt/models/."""
    full_path = os.path.join(MODELS_DIR, relative_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_jinja(sql):
    """Replace Jinja {{ ref() }} and {{ source() }} with schema-qualified names."""
    # {{ source('raw', 'table_name') }} -> public.table_name
    sql = re.sub(
        r"\{\{\s*source\s*\(\s*'raw'\s*,\s*'(\w+)'\s*\)\s*\}\}",
        lambda m: f"public.{m.group(1)}",
        sql,
    )
    # {{ ref('stg_*') }} -> public_staging.stg_*
    sql = re.sub(
        r"\{\{\s*ref\s*\(\s*'(stg_\w+)'\s*\)\s*\}\}",
        lambda m: f"public_staging.{m.group(1)}",
        sql,
    )
    # {{ ref('int_*') }} -> _int_*.* (temp tables)
    sql = re.sub(
        r"\{\{\s*ref\s*\(\s*'(int_\w+)'\s*\)\s*\}\}",
        lambda m: f"public_analytics._tmp_{m.group(1)}",
        sql,
    )
    # {{ ref('dim_*_seed') }} -> public_analytics.dim_*_seed
    sql = re.sub(
        r"\{\{\s*ref\s*\(\s*'(\w+_seed)'\s*\)\s*\}\}",
        lambda m: f"public_analytics.{m.group(1)}",
        sql,
    )
    # {{ ref('dim_*') }} or {{ ref('fact_*') }} -> public_analytics.*
    sql = re.sub(
        r"\{\{\s*ref\s*\(\s*'((?:dim|fact)_\w+)'\s*\)\s*\}\}",
        lambda m: f"public_analytics.{m.group(1)}",
        sql,
    )
    return sql


def execute_sql(cur, sql, label):
    """Execute SQL with timing and error handling."""
    start = time.time()
    try:
        cur.execute(sql)
        elapsed = time.time() - start
        if cur.description:
            rows = cur.fetchall()
            print(f"  OK  {label} ({elapsed:.1f}s) -> {len(rows)} rows")
            return rows
        elif cur.rowcount and cur.rowcount >= 0:
            print(f"  OK  {label} ({elapsed:.1f}s) -> {cur.rowcount} rows affected")
        else:
            print(f"  OK  {label} ({elapsed:.1f}s)")
        return None
    except psycopg2.Error as exc:
        elapsed = time.time() - start
        print(f"  ERR {label} ({elapsed:.1f}s) -> {exc.pgerror or exc}")
        raise


def phase_a_seeds(cur):
    """Phase A: Load seed CSVs into public_analytics."""
    print("\n" + "=" * 60)
    print("  PHASE A: Seeds")
    print("=" * 60)

    seeds = [
        "dim_channel_seed",
        "dim_event_type_seed",
        "dim_time_seed",
        "dim_contact_reason_seed",
    ]

    for seed_name in seeds:
        csv_path = os.path.join(SEEDS_DIR, f"{seed_name}.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        cols = ", ".join(headers)
        placeholders = ", ".join(["%s"] * len(headers))

        cur.execute(f"DROP TABLE IF EXISTS public_analytics.{seed_name} CASCADE")
        # Infer types from seed name and known schemas
        col_defs = []
        for h in headers:
            if h.endswith("_key") or h == "ordinal" or h == "display_order" or h == "level" or h == "parent_key":
                col_defs.append(f"{h} integer")
            elif h.startswith("is_"):
                col_defs.append(f"{h} boolean")
            else:
                col_defs.append(f"{h} varchar(255)")
        create_sql = f"CREATE TABLE public_analytics.{seed_name} ({', '.join(col_defs)})"
        cur.execute(create_sql)

        for row in rows:
            # Cast types
            typed_row = []
            for i, val in enumerate(row):
                if val == "" or val is None:
                    typed_row.append(None)
                elif headers[i].endswith("_key") or headers[i] in ("ordinal", "display_order", "level", "parent_key"):
                    typed_row.append(int(val))
                elif headers[i].startswith("is_"):
                    typed_row.append(val.lower() == "true")
                else:
                    typed_row.append(val)
            cur.execute(
                f"INSERT INTO public_analytics.{seed_name} ({cols}) VALUES ({placeholders})",
                typed_row,
            )
        print(f"  OK  {seed_name} -> {len(rows)} rows")


def phase_b_staging(cur):
    """Phase B: Create staging views in public_staging."""
    print("\n" + "=" * 60)
    print("  PHASE B: Staging views")
    print("=" * 60)

    staging_models = [
        "stg_messages",
        "stg_contacts",
        "stg_agents",
        "stg_toques_daily",
        "stg_campaigns",
        "stg_chat_conversations",
        "stg_chat_topics",
        "stg_sms_envios",
    ]

    for model in staging_models:
        sql = read_sql_file(f"staging/{model}.sql")
        sql = resolve_jinja(sql)
        # Strip comment lines at the top
        view_sql = f"CREATE OR REPLACE VIEW public_staging.{model} AS\n{sql}"
        execute_sql(cur, view_sql, model)


def phase_c_intermediate(cur):
    """Phase C: Create intermediate models as temp tables in public_analytics."""
    print("\n" + "=" * 60)
    print("  PHASE C: Intermediate (temp tables)")
    print("=" * 60)

    # Order matters — dependencies must be built first
    intermediate_models = [
        "int_messages_classified",
        "int_sms_events_unpivoted",
        "int_toques_events_unpivoted",
        "int_conversations_enriched",
        "int_dim_contact_unified",
        "int_bot_intent_bridge",
        "int_conversation_sessions",
    ]

    for model in intermediate_models:
        sql = read_sql_file(f"intermediate/{model}.sql")
        sql = resolve_jinja(sql)
        cur.execute(f"DROP TABLE IF EXISTS public_analytics._tmp_{model} CASCADE")
        table_sql = f"CREATE TABLE public_analytics._tmp_{model} AS\n{sql}"
        execute_sql(cur, table_sql, model)


def phase_d_ref_dims(cur):
    """Phase D: Create reference dimension tables."""
    print("\n" + "=" * 60)
    print("  PHASE D: Reference dimensions")
    print("=" * 60)

    ref_dims = [
        "dim_date",
        "dim_time",
        "dim_channel",
        "dim_event_type",
        "dim_tenant",
        "dim_contact_reason",
    ]

    for model in ref_dims:
        sql = read_sql_file(f"marts/analytics/{model}.sql")
        sql = resolve_jinja(sql)
        cur.execute(f"DROP TABLE IF EXISTS public_analytics.{model} CASCADE")
        table_sql = f"CREATE TABLE public_analytics.{model} AS\n{sql}"
        execute_sql(cur, table_sql, model)


def phase_e_data_dims(cur):
    """Phase E: Create data dimension tables."""
    print("\n" + "=" * 60)
    print("  PHASE E: Data dimensions")
    print("=" * 60)

    data_dims = [
        "dim_contact",
        "dim_agent",
        "dim_campaign",
    ]

    for model in data_dims:
        sql = read_sql_file(f"marts/analytics/{model}.sql")
        sql = resolve_jinja(sql)
        cur.execute(f"DROP TABLE IF EXISTS public_analytics.{model} CASCADE")
        table_sql = f"CREATE TABLE public_analytics.{model} AS\n{sql}"
        execute_sql(cur, table_sql, model)


def phase_f_session_dims(cur):
    """Phase F: Create session dimension tables."""
    print("\n" + "=" * 60)
    print("  PHASE F: Session dimensions")
    print("=" * 60)

    session_dims = [
        "dim_conversation_session",
        "dim_conversation",
    ]

    for model in session_dims:
        sql = read_sql_file(f"marts/analytics/{model}.sql")
        sql = resolve_jinja(sql)
        cur.execute(f"DROP TABLE IF EXISTS public_analytics.{model} CASCADE")
        table_sql = f"CREATE TABLE public_analytics.{model} AS\n{sql}"
        execute_sql(cur, table_sql, model)


def index_dims_for_fact(cur):
    """Index dimension tables + ANALYZE before building fact (critical for JOIN performance)."""
    print("\n  Indexing dimensions for fact build...")
    dim_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_dim_contact_lookup ON public_analytics.dim_contact (tenant_id, contact_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_agent_lookup ON public_analytics.dim_agent (tenant_id, agent_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_campaign_lookup ON public_analytics.dim_campaign (tenant_id, campaign_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_conversation_lookup ON public_analytics.dim_conversation (tenant_id, conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_channel_code ON public_analytics.dim_channel (channel_code)",
        "CREATE INDEX IF NOT EXISTS idx_dim_event_type_code ON public_analytics.dim_event_type (event_code)",
        "CREATE INDEX IF NOT EXISTS idx_dim_tenant_id ON public_analytics.dim_tenant (tenant_id)",
    ]
    for idx_sql in dim_indexes:
        try:
            cur.execute(idx_sql)
        except psycopg2.Error:
            pass
    cur.execute("ANALYZE public_analytics.dim_contact")
    cur.execute("ANALYZE public_analytics.dim_agent")
    cur.execute("ANALYZE public_analytics.dim_campaign")
    cur.execute("ANALYZE public_analytics.dim_conversation")
    cur.execute("ANALYZE public_analytics.dim_channel")
    cur.execute("ANALYZE public_analytics.dim_event_type")
    cur.execute("ANALYZE public_analytics.dim_tenant")
    print("  Done.")


def phase_g_fact(cur):
    """Phase G: Create fact table."""
    print("\n" + "=" * 60)
    print("  PHASE G: Fact table")
    print("=" * 60)

    index_dims_for_fact(cur)

    sql = read_sql_file("marts/analytics/fact_message_events.sql")
    sql = resolve_jinja(sql)
    cur.execute("DROP TABLE IF EXISTS public_analytics.fact_message_events CASCADE")
    table_sql = f"CREATE TABLE public_analytics.fact_message_events AS\n{sql}"
    execute_sql(cur, table_sql, "fact_message_events")


def cleanup_temp_tables(cur):
    """Remove intermediate temp tables."""
    print("\n  Cleaning up temp tables...")
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public_analytics'
          AND table_name LIKE '_tmp_%'
    """)
    for (table_name,) in cur.fetchall():
        cur.execute(f"DROP TABLE IF EXISTS public_analytics.{table_name} CASCADE")
        print(f"  Dropped public_analytics.{table_name}")


def create_indexes(cur):
    """Create performance indexes on analytics tables."""
    print("\n  Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_fact_events_date ON public_analytics.fact_message_events (date_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_events_channel ON public_analytics.fact_message_events (channel_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_events_source ON public_analytics.fact_message_events (source_table)",
        "CREATE INDEX IF NOT EXISTS idx_fact_events_tenant_date ON public_analytics.fact_message_events (tenant_key, date_key)",
        "CREATE INDEX IF NOT EXISTS idx_dim_contact_tenant ON public_analytics.dim_contact (tenant_id, contact_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_agent_tenant ON public_analytics.dim_agent (tenant_id, agent_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_campaign_tenant ON public_analytics.dim_campaign (tenant_id, campaign_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_conversation_tenant ON public_analytics.dim_conversation (tenant_id, conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_dim_conv_session_tenant ON public_analytics.dim_conversation_session (tenant_id, conversation_session_id)",
    ]
    for idx_sql in indexes:
        try:
            cur.execute(idx_sql)
        except psycopg2.Error as exc:
            print(f"  WARN index: {exc.pgerror or exc}")


def validate(cur):
    """Final validation — DRY RUN 4."""
    print("\n" + "=" * 60)
    print("  VALIDATION")
    print("=" * 60)

    cur.execute("""
        SELECT t, rows FROM (
            SELECT 'dim_date' as t, count(*) as rows FROM public_analytics.dim_date
            UNION ALL SELECT 'dim_time', count(*) FROM public_analytics.dim_time
            UNION ALL SELECT 'dim_tenant', count(*) FROM public_analytics.dim_tenant
            UNION ALL SELECT 'dim_channel', count(*) FROM public_analytics.dim_channel
            UNION ALL SELECT 'dim_event_type', count(*) FROM public_analytics.dim_event_type
            UNION ALL SELECT 'dim_contact', count(*) FROM public_analytics.dim_contact
            UNION ALL SELECT 'dim_agent', count(*) FROM public_analytics.dim_agent
            UNION ALL SELECT 'dim_campaign', count(*) FROM public_analytics.dim_campaign
            UNION ALL SELECT 'dim_contact_reason', count(*) FROM public_analytics.dim_contact_reason
            UNION ALL SELECT 'dim_conversation_session', count(*) FROM public_analytics.dim_conversation_session
            UNION ALL SELECT 'dim_conversation', count(*) FROM public_analytics.dim_conversation
            UNION ALL SELECT 'fact_message_events', count(*) FROM public_analytics.fact_message_events
        ) x ORDER BY t
    """)

    all_ok = True
    for table, rows in cur.fetchall():
        status = "OK" if rows > 0 else "EMPTY!"
        if rows == 0:
            all_ok = False
        print(f"  {status:6s} {table:30s} {rows:>10,} rows")

    # FK integrity
    cur.execute("""
        SELECT 'orphan_date' as check_name, count(*) FROM public_analytics.fact_message_events f
          LEFT JOIN public_analytics.dim_date d ON d.date_key = f.date_key WHERE d.date_key IS NULL
        UNION ALL SELECT 'orphan_channel', count(*) FROM public_analytics.fact_message_events f
          LEFT JOIN public_analytics.dim_channel c ON c.channel_key = f.channel_key WHERE c.channel_key IS NULL
        UNION ALL SELECT 'orphan_event', count(*) FROM public_analytics.fact_message_events f
          LEFT JOIN public_analytics.dim_event_type e ON e.event_type_key = f.event_type_key WHERE e.event_type_key IS NULL
        UNION ALL SELECT 'orphan_tenant', count(*) FROM public_analytics.fact_message_events f
          LEFT JOIN public_analytics.dim_tenant t ON t.tenant_key = f.tenant_key WHERE t.tenant_key IS NULL
    """)

    print("\n  FK integrity:")
    for check_name, count in cur.fetchall():
        status = "OK" if count == 0 else f"FAIL ({count:,})"
        print(f"  {status:10s} {check_name}")
        if count > 0:
            all_ok = False

    # Source table breakdown
    cur.execute("""
        SELECT source_table, count(*), min(date_key), max(date_key)
        FROM public_analytics.fact_message_events
        GROUP BY 1 ORDER BY 2 DESC
    """)
    print("\n  Source breakdown:")
    for source, cnt, min_dk, max_dk in cur.fetchall():
        print(f"  {source:25s} {cnt:>10,} rows | {min_dk} -> {max_dk}")

    return all_ok


def main():
    start_time = time.time()
    conn = get_db()
    cur = conn.cursor()

    # Ensure schemas exist
    cur.execute("CREATE SCHEMA IF NOT EXISTS public_staging")
    cur.execute("CREATE SCHEMA IF NOT EXISTS public_analytics")

    phases = {
        "A": phase_a_seeds,
        "B": phase_b_staging,
        "C": phase_c_intermediate,
        "D": phase_d_ref_dims,
        "E": phase_e_data_dims,
        "F": phase_f_session_dims,
        "G": phase_g_fact,
    }

    if DRY_RUN:
        print("DRY RUN — validating only")
        ok = validate(cur)
        cur.close()
        conn.close()
        sys.exit(0 if ok else 1)

    for phase_key, phase_fn in phases.items():
        if PHASE_FILTER and phase_key != PHASE_FILTER:
            continue
        phase_fn(cur)

    if not PHASE_FILTER:
        cleanup_temp_tables(cur)
        create_indexes(cur)
        ok = validate(cur)

        elapsed = time.time() - start_time
        print(f"\n{'=' * 60}")
        status = "SUCCESS" if ok else "COMPLETED WITH WARNINGS"
        print(f"  {status} in {elapsed:.0f}s")
        print(f"{'=' * 60}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
