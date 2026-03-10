"""Schema introspection endpoints."""
import io
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from app.models.database import engine
from app.services.schema_service import ALLOWED_TABLES, ANALYTICS_TABLES, SchemaService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tables")
async def list_tables(live_counts: bool = False):
    svc = SchemaService()
    try:
        return svc.list_all_tables_with_columns(live_counts=live_counts)
    except Exception as e:
        logger.warning("SchemaService.list_all_tables_with_columns failed: %s", e)
        try:
            tables = svc.list_tables(live_counts=live_counts)
            return [{"table_name": t["table_name"], "row_count": t["row_count"], "size": t["size"], "schema": "public", "columns": []} for t in tables]
        except Exception:
            return []


@router.get("/tables/{table_name}")
async def get_table_detail(table_name: str, schema: str = "public"):
    svc = SchemaService()
    columns = svc.get_table_schema(table_name, schema)
    if not columns:
        raise HTTPException(status_code=404, detail="Table not found or not allowed")
    return {"table_name": table_name, "schema": schema, "columns": columns}


@router.get("/tables/{table_name}/preview")
async def preview_table(table_name: str, limit: int = 50, schema: str = "public"):
    svc = SchemaService()
    df = svc.preview_table(table_name, limit=min(limit, 200), schema=schema)
    if df.empty:
        return {"columns": [], "data": [], "total": 0}
    return {
        "columns": list(df.columns),
        "data": df.to_dict("records"),
        "total": len(df),
    }


@router.get("/tables/{table_name}/profile")
async def profile_table(table_name: str):
    svc = SchemaService()
    return svc.get_table_profile(table_name)


@router.get("/tables/{table_name}/download")
async def download_table(
    table_name: str,
    limit: int = Query(default=1000, ge=1, le=100000),
    schema: str = Query(default="public"),
):
    """Download table data as UTF-8 CSV with BOM."""
    # Validate table_name against allowed tables to prevent SQL injection
    if schema == "public" and table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=403, detail="Table not allowed")
    if schema == "public_marts" and table_name not in ANALYTICS_TABLES:
        raise HTTPException(status_code=403, detail="Table not allowed")
    if schema not in ("public", "public_marts"):
        raise HTTPException(status_code=400, detail="Invalid schema")

    qualified = f'"{schema}"."{table_name}"'
    query = text(f"SELECT * FROM {qualified} LIMIT :lim")

    try:
        import pandas as pd

        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"lim": limit})
    except Exception as e:
        logger.error("Failed to download table %s.%s: %s", schema, table_name, e)
        raise HTTPException(status_code=500, detail="Error reading table data")

    # Convert to CSV with BOM for Excel compatibility
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM
    df.to_csv(buf, index=False)
    buf.seek(0)

    filename = f"{schema}_{table_name}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
