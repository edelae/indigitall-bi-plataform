"""
Seed script — loads CSV demo data into PostgreSQL.

Usage:
    docker compose exec app python scripts/seed_data.py
    # or locally:
    python scripts/seed_data.py
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine, create_tables

# Path to demo CSVs
DEMO_DATA = Path(__file__).resolve().parent.parent.parent / "Demo" / "app" / "data" / "processed"
TOQUES_DATA = DEMO_DATA / "toques"

DEFAULT_TENANT = "demo"


def clean_boolean(val):
    """Convert string Yes/No to Python bool."""
    if isinstance(val, str):
        return val.strip().lower() in ("yes", "true", "1")
    return bool(val)


def safe_int(val, default=0):
    """Safely convert to int, handling strings and NaN."""
    try:
        if pd.isna(val):
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def seed_messages():
    csv = DEMO_DATA / "messages.csv"
    if not csv.exists():
        print(f"  SKIP messages — {csv} not found")
        return

    df = pd.read_csv(csv, parse_dates=["timestamp", "date"])

    # Map entity → tenant_id
    df["tenant_id"] = df["entity"].fillna(DEFAULT_TENANT)

    # Clean booleans
    for col in ["is_fallback", "is_bot", "is_human"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_boolean)

    # Clean integers
    for col in ["wait_time_seconds", "handle_time_seconds"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: safe_int(v, None))

    # Drop entity (we use tenant_id now)
    df = df.drop(columns=["entity"], errors="ignore")

    df.to_sql("messages", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"  messages: {len(df)} rows")


def seed_contacts():
    csv = DEMO_DATA / "contacts.csv"
    if not csv.exists():
        print(f"  SKIP contacts — {csv} not found")
        return

    df = pd.read_csv(csv)
    df["tenant_id"] = df["entity"].fillna(DEFAULT_TENANT)
    df = df.drop(columns=["entity"], errors="ignore")
    df.to_sql("contacts", engine, if_exists="append", index=False)
    print(f"  contacts: {len(df)} rows")


def seed_agents():
    csv = DEMO_DATA / "agents.csv"
    if not csv.exists():
        print(f"  SKIP agents — {csv} not found")
        return

    df = pd.read_csv(csv)
    df["tenant_id"] = DEFAULT_TENANT

    # CSV has avg_handle_time_minutes — convert to seconds
    if "avg_handle_time_minutes" in df.columns:
        df["avg_handle_time_seconds"] = (df["avg_handle_time_minutes"] * 60).astype(int)
        df = df.drop(columns=["avg_handle_time_minutes"], errors="ignore")

    # Drop avg_handle_time_seconds if it was already there from CSV
    if "avg_handle_time_seconds" not in df.columns and "avg_handle_time_seconds" in df.columns:
        pass  # already there

    df.to_sql("agents", engine, if_exists="append", index=False)
    print(f"  agents: {len(df)} rows")


def seed_daily_stats():
    csv = DEMO_DATA / "daily_stats.csv"
    if not csv.exists():
        print(f"  SKIP daily_stats — {csv} not found")
        return

    df = pd.read_csv(csv, parse_dates=["date"])
    df["tenant_id"] = DEFAULT_TENANT

    # Fix fallback_count — may be concatenated strings
    df["fallback_count"] = df["fallback_count"].apply(safe_int)

    df.to_sql("daily_stats", engine, if_exists="append", index=False)
    print(f"  daily_stats: {len(df)} rows")


def seed_toques_daily():
    csv = TOQUES_DATA / "toques_daily.csv"
    if not csv.exists():
        print(f"  SKIP toques_daily — {csv} not found")
        return

    df = pd.read_csv(csv, parse_dates=["date"])
    df["tenant_id"] = df["proyecto_cuenta"].fillna(DEFAULT_TENANT)

    df.to_sql("toques_daily", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"  toques_daily: {len(df)} rows")


def seed_campaigns():
    csv = TOQUES_DATA / "campanas_summary.csv"
    if not csv.exists():
        print(f"  SKIP campaigns — {csv} not found")
        return

    df = pd.read_csv(csv, parse_dates=["fecha_inicio", "fecha_fin"])
    df["tenant_id"] = df["proyecto_cuenta"].fillna(DEFAULT_TENANT)

    df.to_sql("campaigns", engine, if_exists="append", index=False)
    print(f"  campaigns: {len(df)} rows")


def seed_heatmap():
    csv = TOQUES_DATA / "toques_heatmap.csv"
    if not csv.exists():
        print(f"  SKIP toques_heatmap — {csv} not found")
        return

    df = pd.read_csv(csv)
    df["tenant_id"] = DEFAULT_TENANT

    df.to_sql("toques_heatmap", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"  toques_heatmap: {len(df)} rows")


def seed_usuario():
    csv = TOQUES_DATA / "toques_usuario.csv"
    if not csv.exists():
        print(f"  SKIP toques_usuario — {csv} not found")
        return

    df = pd.read_csv(csv, parse_dates=["primer_toque", "ultimo_toque"])
    df["tenant_id"] = df["proyecto_cuenta"].fillna(DEFAULT_TENANT)

    # This table is large (~675K rows) — use chunked insert
    df.to_sql("toques_usuario", engine, if_exists="append", index=False, method="multi", chunksize=10000)
    print(f"  toques_usuario: {len(df)} rows")


def main():
    print("=== Creating tables ===")
    create_tables()

    print("\n=== Truncating existing data ===")
    tables = [
        "messages", "contacts", "agents", "daily_stats",
        "toques_daily", "campaigns", "toques_heatmap", "toques_usuario",
    ]
    with engine.begin() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
    print("  Done")

    print("\n=== Seeding data ===")
    seed_messages()
    seed_contacts()
    seed_agents()
    seed_daily_stats()
    seed_toques_daily()
    seed_campaigns()
    seed_heatmap()
    seed_usuario()

    print("\n=== Seed complete ===")


if __name__ == "__main__":
    main()
