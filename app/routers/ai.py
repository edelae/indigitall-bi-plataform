"""AI chat endpoint + direct SQL execution."""
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import pandas as pd
from sqlalchemy import text

from app.config import settings
from app.models.database import engine

logger = logging.getLogger(__name__)
router = APIRouter()

SQL_BLOCKLIST = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|DO|CALL|SET\s+ROLE|pg_sleep|dblink)\b",
    re.IGNORECASE,
)


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    tenant: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    data: List[Dict[str, Any]] = []
    columns: List[str] = []
    chart_type: Optional[str] = None
    query_details: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    from app.services.data_service import DataService
    from app.services.ai_agent import AIAgent

    tenant = req.tenant or settings.DEFAULT_TENANT
    data_svc = DataService()
    agent = AIAgent(data_svc)

    result = agent.process_query(
        user_question=req.message,
        conversation_history=req.conversation_history or [],
        tenant_filter=tenant,
    )

    df = result.get("data")
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        data_records = df.to_dict("records")
        columns = list(df.columns)
    else:
        data_records = []
        columns = []

    return ChatResponse(
        response=result.get("response", ""),
        data=data_records,
        columns=columns,
        chart_type=result.get("chart_type"),
        query_details=result.get("query_details"),
    )


class SqlRequest(BaseModel):
    sql: str
    tenant: Optional[str] = None


@router.post("/execute-sql")
async def execute_sql(req: SqlRequest):
    """Execute a read-only SQL query directly (with guardrails)."""
    sql = req.sql.strip()
    if not sql:
        raise HTTPException(400, "SQL vacio")
    if SQL_BLOCKLIST.search(sql):
        raise HTTPException(400, "SQL contiene operaciones no permitidas (solo SELECT)")
    if not sql.upper().lstrip().startswith("SELECT"):
        raise HTTPException(400, "Solo se permiten consultas SELECT")

    try:
        with engine.connect() as conn:
            conn.execute(text("SET statement_timeout = '10s'"))
            df = pd.read_sql(text(sql), conn)
            if len(df) > 1000:
                df = df.head(1000)
        return {
            "data": df.to_dict("records"),
            "columns": list(df.columns),
            "row_count": len(df),
        }
    except Exception as e:
        raise HTTPException(400, f"Error ejecutando SQL: {str(e)[:300]}")
