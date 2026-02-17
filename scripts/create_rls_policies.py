"""
Create Row-Level Security policies for all tenant-scoped tables.

Usage:
    docker compose exec app python scripts/create_rls_policies.py
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import engine

TABLES = [
    "messages",
    "contacts",
    "agents",
    "daily_stats",
    "toques_daily",
    "campaigns",
    "toques_heatmap",
    "toques_usuario",
    "saved_queries",
    "dashboards",
]


def main():
    print("=== Creating RLS policies ===\n")

    with engine.begin() as conn:
        for table in TABLES:
            print(f"  {table}:")

            # Enable RLS
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            print(f"    RLS enabled")

            # Drop existing policy if any (idempotent)
            conn.execute(text(
                f"DROP POLICY IF EXISTS tenant_isolation ON {table}"
            ))

            # Create policy: rows visible only when tenant_id matches session var
            conn.execute(text(f"""
                CREATE POLICY tenant_isolation ON {table}
                    USING (tenant_id = current_setting('app.current_tenant', true))
            """))
            print(f"    Policy 'tenant_isolation' created")

            # Allow the app user to bypass RLS (service role)
            # The app sets the tenant context then queries as postgres
            conn.execute(text(
                f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"
            ))
            print(f"    Force RLS for table owner")

        # Create helper function
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION set_tenant_context(tid TEXT)
            RETURNS VOID AS $$
            BEGIN
                PERFORM set_config('app.current_tenant', tid, true);
            END;
            $$ LANGUAGE plpgsql;
        """))
        print(f"\n  Helper function set_tenant_context() created")

    print("\n=== RLS setup complete ===")


if __name__ == "__main__":
    main()
