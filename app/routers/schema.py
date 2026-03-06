"""Schema introspection endpoints."""
import logging
from fastapi import APIRouter, HTTPException

from app.services.schema_service import SchemaService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/tables")
async def list_tables():
    svc = SchemaService()
    try:
        return svc.list_all_tables_with_columns()
    except Exception as e:
        logger.warning("SchemaService.list_all_tables_with_columns failed: %s", e)
        try:
            tables = svc.list_tables()
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
