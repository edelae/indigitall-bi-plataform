"""Database engine and session configuration."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    """Yield a database session with tenant context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant(db, tenant_id: str):
    """Set the RLS tenant context for a session."""
    db.execute(text("SET LOCAL app.current_tenant = :tid"), {"tid": tenant_id})


def create_tables():
    """Create all tables defined in schemas."""
    from app.models.schemas import (  # noqa: F401
        Message, Contact, Agent, DailyStat,
        ToquesDaily, Campaign, ToquesHeatmap, ToquesUsuario,
        SavedQuery, Dashboard, SyncState,
    )
    Base.metadata.create_all(bind=engine)
