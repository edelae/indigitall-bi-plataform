from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/api/health")
async def health():
    return {"status": "ok", "auth_mode": settings.AUTH_MODE}
