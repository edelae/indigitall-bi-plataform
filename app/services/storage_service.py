"""
Storage Service — PostgreSQL-backed saved queries and dashboards.
Replaces Demo filesystem storage with saved_queries + dashboards tables.
All items are shared tenant-wide (no private/published distinction).
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from sqlalchemy import select, update, delete, func, and_, or_

from app.models.database import engine
from app.models.schemas import SavedQuery, Dashboard


class StorageService:
    """Service for managing saved queries and dashboards."""

    def __init__(self, tenant_id: str = "demo"):
        self.tenant_id = tenant_id

    # ==================== Saved Queries ====================

    def list_queries(
        self,
        favorites_only: bool = False,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        t = SavedQuery.__table__
        clauses = [t.c.tenant_id == self.tenant_id, t.c.is_archived == False]  # noqa: E712

        if favorites_only:
            clauses.append(t.c.is_favorite == True)  # noqa: E712
        if search:
            clauses.append(t.c.name.ilike(f"%{search}%"))
        if tags:
            clauses.append(t.c.tags.overlap(tags))

        stmt = (
            select(t.c.id, t.c.name, t.c.query_text, t.c.ai_function,
                   t.c.result_row_count, t.c.tags, t.c.is_favorite,
                   t.c.created_by, t.c.created_at, t.c.updated_at)
            .where(and_(*clauses))
            .order_by(t.c.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        count_stmt = select(func.count()).where(and_(*clauses))

        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            total = conn.execute(count_stmt).scalar()

        return {
            "queries": [dict(r) for r in rows],
            "total": total,
        }

    def get_query(self, query_id: int) -> Optional[Dict[str, Any]]:
        t = SavedQuery.__table__
        stmt = select(t).where(and_(t.c.id == query_id, t.c.tenant_id == self.tenant_id))

        with engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()

        if not row:
            return None

        result = dict(row)
        # Convert result_data back to DataFrame for compatibility
        if result.get("result_data"):
            result["dataframe"] = pd.DataFrame(result["result_data"])
        else:
            result["dataframe"] = pd.DataFrame()

        return result

    def save_query(
        self,
        name: str,
        query_text: str,
        data: pd.DataFrame,
        ai_function: Optional[str] = None,
        generated_sql: Optional[str] = None,
        visualizations: Optional[List[Dict]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        t = SavedQuery.__table__
        now = datetime.utcnow()

        values = {
            "tenant_id": self.tenant_id,
            "name": name,
            "query_text": query_text,
            "ai_function": ai_function,
            "generated_sql": generated_sql,
            "result_data": data.to_dict("records") if not data.empty else [],
            "result_columns": [{"name": c, "type": str(data[c].dtype)} for c in data.columns] if not data.empty else [],
            "result_row_count": len(data),
            "visualizations": visualizations or [],
            "tags": tags,
            "is_favorite": False,
            "is_archived": False,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        with engine.begin() as conn:
            result = conn.execute(t.insert().values(**values).returning(t.c.id))
            new_id = result.scalar()

        return {"success": True, "id": new_id, "name": name}

    def archive_query(self, query_id: int) -> Dict[str, Any]:
        t = SavedQuery.__table__
        stmt = (
            update(t)
            .where(and_(t.c.id == query_id, t.c.tenant_id == self.tenant_id))
            .values(is_archived=True, updated_at=datetime.utcnow())
        )
        with engine.begin() as conn:
            result = conn.execute(stmt)
        return {"success": result.rowcount > 0}

    def toggle_favorite_query(self, query_id: int) -> Dict[str, Any]:
        t = SavedQuery.__table__
        # Get current state
        with engine.connect() as conn:
            row = conn.execute(
                select(t.c.is_favorite).where(and_(t.c.id == query_id, t.c.tenant_id == self.tenant_id))
            ).first()

        if not row:
            return {"success": False, "error": "Query not found"}

        with engine.begin() as conn:
            conn.execute(
                update(t)
                .where(and_(t.c.id == query_id, t.c.tenant_id == self.tenant_id))
                .values(is_favorite=not row.is_favorite, updated_at=datetime.utcnow())
            )

        return {"success": True, "is_favorite": not row.is_favorite}

    # ==================== Dashboards ====================

    def list_dashboards(
        self,
        favorites_only: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        t = Dashboard.__table__
        clauses = [t.c.tenant_id == self.tenant_id, t.c.is_archived == False]  # noqa: E712

        if favorites_only:
            clauses.append(t.c.is_favorite == True)  # noqa: E712
        if search:
            clauses.append(t.c.name.ilike(f"%{search}%"))

        stmt = (
            select(t.c.id, t.c.name, t.c.description, t.c.tags,
                   t.c.is_favorite, t.c.is_default, t.c.created_by,
                   t.c.created_at, t.c.updated_at)
            .where(and_(*clauses))
            .order_by(t.c.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        count_stmt = select(func.count()).where(and_(*clauses))

        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            total = conn.execute(count_stmt).scalar()

        return {
            "dashboards": [dict(r) for r in rows],
            "total": total,
        }

    def get_dashboard(self, dashboard_id: int) -> Optional[Dict[str, Any]]:
        t = Dashboard.__table__
        stmt = select(t).where(and_(t.c.id == dashboard_id, t.c.tenant_id == self.tenant_id))

        with engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()

        return dict(row) if row else None

    def save_dashboard(
        self,
        name: str,
        layout: Optional[List[Dict]] = None,
        description: Optional[str] = None,
        filters: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        is_default: bool = False,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        t = Dashboard.__table__
        now = datetime.utcnow()

        values = {
            "tenant_id": self.tenant_id,
            "name": name,
            "description": description,
            "layout": layout or [],
            "filters": filters,
            "tags": tags,
            "is_favorite": False,
            "is_archived": False,
            "is_default": is_default,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        with engine.begin() as conn:
            result = conn.execute(t.insert().values(**values).returning(t.c.id))
            new_id = result.scalar()

        return {"success": True, "id": new_id, "name": name}

    def update_dashboard_layout(self, dashboard_id: int, layout: List[Dict],
                                 updated_by: Optional[str] = None) -> Dict[str, Any]:
        t = Dashboard.__table__
        stmt = (
            update(t)
            .where(and_(t.c.id == dashboard_id, t.c.tenant_id == self.tenant_id))
            .values(layout=layout, updated_at=datetime.utcnow(), updated_by=updated_by)
        )
        with engine.begin() as conn:
            result = conn.execute(stmt)
        return {"success": result.rowcount > 0}

    def archive_dashboard(self, dashboard_id: int) -> Dict[str, Any]:
        t = Dashboard.__table__
        stmt = (
            update(t)
            .where(and_(t.c.id == dashboard_id, t.c.tenant_id == self.tenant_id))
            .values(is_archived=True, updated_at=datetime.utcnow())
        )
        with engine.begin() as conn:
            result = conn.execute(stmt)
        return {"success": result.rowcount > 0}

    def toggle_favorite_dashboard(self, dashboard_id: int) -> Dict[str, Any]:
        t = Dashboard.__table__
        with engine.connect() as conn:
            row = conn.execute(
                select(t.c.is_favorite).where(and_(t.c.id == dashboard_id, t.c.tenant_id == self.tenant_id))
            ).first()

        if not row:
            return {"success": False, "error": "Dashboard not found"}

        with engine.begin() as conn:
            conn.execute(
                update(t)
                .where(and_(t.c.id == dashboard_id, t.c.tenant_id == self.tenant_id))
                .values(is_favorite=not row.is_favorite, updated_at=datetime.utcnow())
            )

        return {"success": True, "is_favorite": not row.is_favorite}
