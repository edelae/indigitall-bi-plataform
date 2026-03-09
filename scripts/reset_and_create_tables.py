"""
Reset database tables and create new ones.

Truncates all data tables (preserving saved_queries and dashboards),
creates new SMS tables, and clears raw tables for fresh extraction.

Usage:
    python scripts/reset_and_create_tables.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, inspect
from app.models.database import engine, Base
from app.models import schemas  # noqa: F401 — registers all models


def main():
    print("=" * 60)
    print("  Database Reset & Table Creation")
    print("=" * 60)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names(schema="public")
    print(f"\n  Existing tables: {len(existing_tables)}")

    # Tables to preserve (user data)
    PRESERVE = {"saved_queries", "dashboards"}

    # Tables to truncate (data tables)
    DATA_TABLES = [
        "messages", "contacts", "agents", "daily_stats",
        "chat_conversations", "chat_topics", "chat_channels",
        "toques_daily", "toques_heatmap", "campaigns", "toques_usuario",
        "sms_envios", "sync_state",
    ]

    # New tables to create
    NEW_TABLES = ["sms_campaigns", "sms_contacts", "sms_daily_stats"]

    with engine.begin() as conn:
        # Step 1: Truncate data tables (CASCADE to handle FK dependencies)
        print("\n--- Step 1: Truncating data tables ---")
        for table in DATA_TABLES:
            if table in existing_tables:
                try:
                    conn.execute(text(f"TRUNCATE TABLE public.{table} CASCADE"))
                    print(f"  TRUNCATED: {table}")
                except Exception as e:
                    print(f"  [SKIP] {table}: {e}")
            else:
                print(f"  [NOT FOUND] {table}")

        # Step 2: Clear raw tables
        print("\n--- Step 2: Clearing raw tables ---")
        raw_tables = inspector.get_table_names(schema="raw")
        for table in raw_tables:
            try:
                conn.execute(text(f"TRUNCATE TABLE raw.{table}"))
                print(f"  TRUNCATED: raw.{table}")
            except Exception as e:
                print(f"  [SKIP] raw.{table}: {e}")

    # Step 3: Create new tables via SQLAlchemy
    print("\n--- Step 3: Creating new tables ---")
    for table_name in NEW_TABLES:
        if table_name in existing_tables:
            print(f"  [EXISTS] {table_name}")
        else:
            print(f"  CREATING: {table_name}")

    # Create all missing tables
    Base.metadata.create_all(engine)
    print("  All tables synced with SQLAlchemy models")

    # Step 4: Verify
    print("\n--- Step 4: Verification ---")
    inspector2 = inspect(engine)
    final_tables = inspector2.get_table_names(schema="public")
    print(f"  Total tables: {len(final_tables)}")
    for t in sorted(final_tables):
        with engine.connect() as conn:
            try:
                count = conn.execute(text(f"SELECT count(*) FROM public.{t}")).scalar()
                preserved = " [PRESERVED]" if t in PRESERVE else ""
                print(f"    {t:<25s} {count:>8,} rows{preserved}")
            except Exception:
                print(f"    {t:<25s} [ERROR reading]")

    print(f"\n{'=' * 60}")
    print("  Done. Database ready for fresh extraction.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
