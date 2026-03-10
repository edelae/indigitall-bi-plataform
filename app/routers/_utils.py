"""Shared helpers for API routers."""

import math
from datetime import date, datetime
from typing import Any, Optional, Tuple

import pandas as pd


def sanitize(obj: Any) -> Any:
    """Replace NaN / Infinity floats with None so JSON serialization succeeds."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (date, datetime)):
        return str(obj)
    return obj


def parse_dates(
    start_date: Optional[str], end_date: Optional[str]
) -> Tuple[Optional[date], Optional[date]]:
    """Parse ISO date strings into date objects."""
    s = date.fromisoformat(start_date) if start_date else None
    e = date.fromisoformat(end_date) if end_date else None
    return s, e


def df_to_response(df: pd.DataFrame) -> dict:
    """Convert a DataFrame to a JSON-safe dict with columns and data."""
    if df is None or df.empty:
        return {"columns": [], "data": []}
    records = df.to_dict(orient="records")
    return {
        "columns": list(df.columns),
        "data": sanitize(records),
    }
