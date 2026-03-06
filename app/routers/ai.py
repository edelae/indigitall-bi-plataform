"""AI chat endpoint."""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


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
