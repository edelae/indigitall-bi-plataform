"""Dashboard CRUD."""
import math
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


def _sanitize(obj: Any) -> Any:
    """Replace NaN / Infinity floats with None so JSON serialization succeeds."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


class SaveDashboardRequest(BaseModel):
    name: str
    description: Optional[str] = None
    layout: List[Dict[str, Any]] = []
    tenant: Optional[str] = None


class UpdateLayoutRequest(BaseModel):
    layout: List[Dict[str, Any]]
    tenant: Optional[str] = None


@router.get("")
async def list_dashboards(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    search: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    result = svc.list_dashboards(
        limit=limit, offset=offset,
        favorites_only=favorites_only, search=search,
    )
    for d in result["dashboards"]:
        for key in ("created_at", "updated_at"):
            if d.get(key):
                d[key] = str(d[key])
    return _sanitize(result)


@router.get("/{dashboard_id}")
async def get_dashboard(dashboard_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    dashboard = svc.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    for key in ("created_at", "updated_at"):
        if dashboard.get(key):
            dashboard[key] = str(dashboard[key])
    return _sanitize(dashboard)


@router.post("")
async def save_dashboard(req: SaveDashboardRequest):
    svc = StorageService(tenant_id=req.tenant or settings.DEFAULT_TENANT)
    return svc.save_dashboard(
        name=req.name,
        description=req.description,
        layout=req.layout,
    )


@router.put("/{dashboard_id}")
async def update_dashboard(dashboard_id: int, req: UpdateLayoutRequest):
    svc = StorageService(tenant_id=req.tenant or settings.DEFAULT_TENANT)
    return svc.update_dashboard_layout(dashboard_id, req.layout)


@router.post("/{dashboard_id}/archive")
async def archive_dashboard(dashboard_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    return svc.archive_dashboard(dashboard_id)


@router.post("/{dashboard_id}/favorite")
async def toggle_favorite(dashboard_id: int, tenant: Optional[str] = None):
    svc = StorageService(tenant_id=tenant or settings.DEFAULT_TENANT)
    return svc.toggle_favorite_dashboard(dashboard_id)
