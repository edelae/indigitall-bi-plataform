"""Schema Service — Database introspection for the Data Explorer page."""

import pandas as pd
from sqlalchemy import text
from typing import List, Dict, Any, Optional

from app.models.database import engine

# Tables allowed in the Data Explorer (whitelist for security)
ALLOWED_TABLES = {
    "messages", "contacts", "agents", "daily_stats",
    "toques_daily", "campaigns", "toques_heatmap", "toques_usuario",
    "saved_queries", "dashboards", "sync_state",
}


class SchemaService:
    """Introspect the Postgres schema for the Data Explorer."""

    def list_tables(self) -> List[Dict[str, Any]]:
        """List all application tables with row counts."""
        query = text("""
            SELECT
                t.table_name,
                COALESCE(s.n_live_tup, 0) AS row_count,
                pg_size_pretty(pg_total_relation_size(quote_ident(t.table_name))) AS size
            FROM information_schema.tables t
            LEFT JOIN pg_stat_user_tables s
                ON s.relname = t.table_name
            WHERE t.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
              AND t.table_name NOT LIKE 'pg_%'
              AND t.table_name NOT LIKE '_%%'
            ORDER BY COALESCE(s.n_live_tup, 0) DESC
        """)
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {"table_name": r.table_name, "row_count": r.row_count, "size": r.size}
            for r in rows
            if r.table_name in ALLOWED_TABLES
        ]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column definitions for a table."""
        if table_name not in ALLOWED_TABLES:
            return []
        query = text("""
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.ordinal_position
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = :table_name
            ORDER BY c.ordinal_position
        """)
        with engine.connect() as conn:
            rows = conn.execute(query, {"table_name": table_name}).fetchall()
        return [
            {
                "column_name": r.column_name,
                "data_type": r.data_type,
                "nullable": r.is_nullable == "YES",
                "default": r.column_default,
            }
            for r in rows
        ]

    def preview_table(self, table_name: str, limit: int = 50) -> pd.DataFrame:
        """Return the first N rows of a table. Uses whitelist validation."""
        if table_name not in ALLOWED_TABLES:
            return pd.DataFrame()
        limit = min(limit, 200)
        # Safe: table_name is validated against whitelist
        query = text(f'SELECT * FROM "{table_name}" LIMIT :lim')
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params={"lim": limit})

    def get_table_profile(self, table_name: str) -> List[Dict[str, Any]]:
        """Compute basic profiling stats per column: null %, distinct count, min, max."""
        if table_name not in ALLOWED_TABLES:
            return []

        columns = self.get_table_schema(table_name)
        if not columns:
            return []

        # Build a single query that computes stats for each column
        parts = []
        for col in columns:
            cn = col["column_name"]
            safe_cn = cn.replace('"', '""')
            parts.append(f"""
                jsonb_build_object(
                    'column_name', '{safe_cn}',
                    'null_pct', ROUND(100.0 * COUNT(*) FILTER (WHERE "{safe_cn}" IS NULL) / GREATEST(COUNT(*), 1), 1),
                    'distinct_count', COUNT(DISTINCT "{safe_cn}"),
                    'total_count', COUNT(*)
                )
            """)

        if not parts:
            return []

        agg_expr = ", ".join(parts)
        query = text(f'SELECT jsonb_build_array({agg_expr}) AS profile FROM "{table_name}"')

        with engine.connect() as conn:
            row = conn.execute(query).first()

        if not row or not row.profile:
            return []

        return row.profile

    def get_sync_status(self) -> List[Dict[str, Any]]:
        """Return sync_state rows for the status banner."""
        query = text("""
            SELECT entity, last_sync_at, records_synced, status, tenant_id
            FROM sync_state
            ORDER BY entity
        """)
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {
                "entity": r.entity,
                "last_sync_at": str(r.last_sync_at) if r.last_sync_at else "Nunca",
                "records_synced": r.records_synced or 0,
                "status": r.status,
                "tenant_id": r.tenant_id,
            }
            for r in rows
        ]

    def list_all_tables_with_columns(self) -> List[Dict[str, Any]]:
        """List all allowed tables with their columns in a single call (for Redash-style sidebar)."""
        tables = self.list_tables()
        result = []
        for t in tables:
            cols = self.get_table_schema(t["table_name"])
            result.append({
                "table_name": t["table_name"],
                "row_count": t["row_count"],
                "size": t["size"],
                "columns": cols,
            })
        return result

    def get_table_indexes(self, table_name: str) -> List[Dict[str, str]]:
        """Return indexes for a given table."""
        if table_name not in ALLOWED_TABLES:
            return []
        query = text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = :table_name
              AND schemaname = 'public'
            ORDER BY indexname
        """)
        with engine.connect() as conn:
            rows = conn.execute(query, {"table_name": table_name}).fetchall()
        return [{"name": r.indexname, "definition": r.indexdef} for r in rows]
