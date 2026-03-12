"""Saved queries CRUD."""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import pandas as pd

from app.config import settings
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


class SaveQueryRequest(BaseModel):
    name: str
    query_text: str
    data: List[Dict[str, Any]] = []
    columns: List[str] = []
    ai_function: Optional[str] = None
    generated_sql: Optional[str] = None
    chart_type: Optional[str] = "table"
    chart_config: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    tenant: Optional[str] = None


@router.get("")
async def list_queries(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    search: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.list_queries(
        limit=limit, offset=offset,
        favorites_only=favorites_only, search=search,
    )
    # Serialize datetime objects
    for q in result["queries"]:
        for key in ("created_at", "updated_at"):
            if q.get(key):
                q[key] = str(q[key])
    return result


@router.get("/{query_id}")
async def get_query(query_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    query = svc.get_query(query_id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    # Remove non-serializable fields
    query.pop("dataframe", None)
    for key in ("created_at", "updated_at", "last_run_at"):
        if query.get(key):
            query[key] = str(query[key])
    return query


@router.post("")
async def save_query(req: SaveQueryRequest):
    svc = StorageService(tenant_id=req.tenant or settings.DEFAULT_TENANT)
    df = pd.DataFrame(req.data) if req.data else pd.DataFrame()
    result = svc.save_query(
        name=req.name,
        query_text=req.query_text,
        data=df,
        ai_function=req.ai_function,
        generated_sql=req.generated_sql,
        visualizations=[{
            "type": req.chart_type or "table",
            "is_default": True,
            **(req.chart_config or {}),
        }],
        conversation_history=req.conversation_history,
    )
    return result


@router.post("/{query_id}/archive")
async def archive_query(query_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    return svc.archive_query(query_id)


@router.post("/{query_id}/favorite")
async def toggle_favorite(query_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    return svc.toggle_favorite_query(query_id)
