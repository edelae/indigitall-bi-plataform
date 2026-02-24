"""
Phase 4 — End-to-end orchestration pipeline.

Runs in order:
    1. Extract  — call existing extraction pipeline (optional, skippable)
    2. Transform — run transform_bridge.py (raw.* → public.*)
    3. dbt run   — execute staging + marts models
    4. dbt test  — run data quality tests
    5. Report    — summary of rows per table and test results

Usage:
    docker compose exec app python scripts/run_pipeline.py
    python scripts/run_pipeline.py                    # full pipeline
    python scripts/run_pipeline.py --skip-extract     # skip API extraction
    python scripts/run_pipeline.py --skip-dbt         # skip dbt run/test
    python scripts/run_pipeline.py --transform-only   # only transform step
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = PROJECT_ROOT / "dbt"
TENANT_ID = "visionamos"


def run_step(name: str, cmd: list[str], cwd: str | None = None) -> bool:
    """Run a subprocess step. Returns True on success."""
    print(f"\n  [{name}] Running: {' '.join(cmd)}")
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            print(f"  [{name}] Completed in {elapsed:.1f}s")
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n")[-10:]:
                    print(f"    {line}")
            return True
        else:
            print(f"  [{name}] FAILED (exit {result.returncode}) in {elapsed:.1f}s")
            if result.stderr.strip():
                for line in result.stderr.strip().split("\n")[-10:]:
                    print(f"    [err] {line}")
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n")[-10:]:
                    print(f"    [out] {line}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  [{name}] TIMEOUT after 300s")
        return False
    except FileNotFoundError as exc:
        print(f"  [{name}] Command not found: {exc}")
        return False


def report_table_counts():
    """Print row counts for all public tables."""
    tables = [
        "contacts", "toques_daily", "toques_heatmap", "campaigns",
        "daily_stats", "agents", "messages", "toques_usuario",
    ]
    print(f"\n  {'Table':<25s}  {'Rows':>8s}  {'Tenant rows':>12s}")
    print(f"  {'─' * 25}  {'─' * 8}  {'─' * 12}")

    with engine.connect() as conn:
        for table in tables:
            try:
                total = conn.execute(text(f"SELECT count(*) FROM public.{table}")).fetchone()[0]
                tenant = conn.execute(text(
                    f"SELECT count(*) FROM public.{table} WHERE tenant_id = :tid"
                ), {"tid": TENANT_ID}).fetchone()[0]
                print(f"  {table:<25s}  {total:>8d}  {tenant:>12d}")
            except Exception:
                print(f"  {table:<25s}  {'—':>8s}  {'—':>12s}")

    # Sync state
    print(f"\n  Sync State:")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT entity, status, records_synced, last_sync_at
            FROM public.sync_state
            WHERE tenant_id = :tid
            ORDER BY entity
        """), {"tid": TENANT_ID}).fetchall()
        if rows:
            for r in rows:
                ts = r[3].strftime("%Y-%m-%d %H:%M") if r[3] else "never"
                print(f"    {r[0]:<20s}  {r[1]:<10s}  {r[2] or 0:>5d} records  last: {ts}")
        else:
            print(f"    (no sync state entries)")


def main():
    parser = argparse.ArgumentParser(description="Indigitall BI pipeline orchestrator")
    parser.add_argument("--skip-extract", action="store_true", help="Skip API extraction step")
    parser.add_argument("--skip-dbt", action="store_true", help="Skip dbt run/test steps")
    parser.add_argument("--transform-only", action="store_true", help="Only run transform step")
    args = parser.parse_args()

    print("=" * 60)
    print("  Indigitall BI Pipeline — Full Orchestration")
    print("=" * 60)

    pipeline_start = time.time()
    steps_ok = 0
    steps_fail = 0

    # ── Step 1: Extract ──
    if not args.skip_extract and not args.transform_only:
        print(f"\n{'─' * 60}")
        print("  STEP 1/5: Extract (API → raw.*)")
        print(f"{'─' * 60}")
        ok = run_step("extract", [
            sys.executable, "-m", "scripts.extractors.orchestrator"
        ])
        if ok:
            steps_ok += 1
        else:
            steps_fail += 1
            print("  [WARN] Extraction failed — continuing with existing raw data")
    else:
        print(f"\n  [SKIP] Step 1: Extract")

    # ── Step 2: Transform ──
    print(f"\n{'─' * 60}")
    print("  STEP 2/5: Transform (raw.* → public.*)")
    print(f"{'─' * 60}")
    ok = run_step("transform", [
        sys.executable, str(PROJECT_ROOT / "scripts" / "transform_bridge.py")
    ])
    if ok:
        steps_ok += 1
    else:
        steps_fail += 1

    # ── Step 3: dbt run ──
    if not args.skip_dbt and not args.transform_only:
        print(f"\n{'─' * 60}")
        print("  STEP 3/5: dbt run (staging → marts)")
        print(f"{'─' * 60}")
        ok = run_step("dbt-run", ["dbt", "run"], cwd=str(DBT_DIR))
        if ok:
            steps_ok += 1
        else:
            steps_fail += 1
    else:
        print(f"\n  [SKIP] Step 3: dbt run")

    # ── Step 4: dbt test ──
    if not args.skip_dbt and not args.transform_only:
        print(f"\n{'─' * 60}")
        print("  STEP 4/5: dbt test (data quality)")
        print(f"{'─' * 60}")
        ok = run_step("dbt-test", ["dbt", "test"], cwd=str(DBT_DIR))
        if ok:
            steps_ok += 1
        else:
            steps_fail += 1
    else:
        print(f"\n  [SKIP] Step 4: dbt test")

    # ── Step 5: Report ──
    print(f"\n{'─' * 60}")
    print("  STEP 5/5: Report")
    print(f"{'─' * 60}")
    try:
        report_table_counts()
        steps_ok += 1
    except Exception as exc:
        print(f"  [ERROR] Report failed: {exc}")
        steps_fail += 1

    # ── Summary ──
    elapsed = time.time() - pipeline_start
    print(f"\n{'=' * 60}")
    print(f"  Pipeline Complete")
    print(f"{'=' * 60}")
    print(f"  Steps OK   : {steps_ok}")
    print(f"  Steps FAIL : {steps_fail}")
    print(f"  Elapsed    : {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return 0 if steps_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
