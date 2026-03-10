"""FastAPI backend for inDigitall BI Platform."""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings

# Logging
from app.logging_config import setup_logging
setup_logging()

logger = logging.getLogger("app")

# Sentry
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info(
        "AI keys — OpenAI: %s, Anthropic: %s",
        "YES" if settings.has_openai_key else "NO",
        "YES" if settings.has_ai_key else "NO",
    )
    yield


app = FastAPI(title="inDigitall BI Platform", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
from app.routers import health, ai, queries, dashboards, schema, pipeline, analytics  # noqa: E402
app.include_router(health.router, tags=["health"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(queries.router, prefix="/api/queries", tags=["queries"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(schema.router, prefix="/api/schema", tags=["schema"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

# Serve React SPA
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")


@app.get("/health")
async def health_compat():
    return {"status": "ok", "auth_mode": settings.AUTH_MODE}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path:
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse(
        {"detail": "Frontend not built yet"},
        status_code=503,
    )
