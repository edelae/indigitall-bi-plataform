"""SQLAlchemy table definitions — maps to docs/09_data_model_design.md."""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, SmallInteger,
    Numeric, DateTime, Index, UniqueConstraint, ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, TIMESTAMP
from sqlalchemy.sql import func

from app.models.database import Base


# ============================================================
# Conversations Domain
# ============================================================

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    message_id = Column(String(100), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    date = Column(Date, nullable=False)
    hour = Column(SmallInteger, nullable=False)
    day_of_week = Column(String(10), nullable=False)
    send_type = Column(String(30))
    direction = Column(String(20), nullable=False)
    content_type = Column(String(30))
    status = Column(String(20))
    contact_name = Column(String(255))
    contact_id = Column(String(100))
    conversation_id = Column(String(100))
    agent_id = Column(String(100))
    close_reason = Column(String(100))
    intent = Column(String(200))
    is_fallback = Column(Boolean, nullable=False, default=False)
    message_body = Column(Text)
    is_bot = Column(Boolean, nullable=False, default=False)
    is_human = Column(Boolean, nullable=False, default=False)
    wait_time_seconds = Column(Integer)
    handle_time_seconds = Column(Integer)

    __table_args__ = (
        UniqueConstraint("tenant_id", "message_id", name="uq_messages_tenant_msg"),
        ForeignKeyConstraint(
            ["tenant_id", "contact_id"],
            ["contacts.tenant_id", "contacts.contact_id"],
            name="fk_messages_contact",
            ondelete="SET NULL",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.agent_id"],
            name="fk_messages_agent",
            ondelete="SET NULL",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "date"],
            ["daily_stats.tenant_id", "daily_stats.date"],
            name="fk_messages_daily_stats",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("idx_messages_tenant_date", "tenant_id", "date"),
        Index("idx_messages_tenant_direction", "tenant_id", "direction"),
        Index("idx_messages_contact", "tenant_id", "contact_id"),
        Index("idx_messages_conversation", "tenant_id", "conversation_id"),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    contact_id = Column(String(100), nullable=False)
    contact_name = Column(String(255))
    total_messages = Column(Integer, nullable=False, default=0)
    first_contact = Column(Date)
    last_contact = Column(Date)
    total_conversations = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "contact_id", name="uq_contacts_tenant_cid"),
    )


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    agent_id = Column(String(100), nullable=False)
    total_messages = Column(Integer, nullable=False, default=0)
    conversations_handled = Column(Integer, nullable=False, default=0)
    avg_handle_time_seconds = Column(Integer)

    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_id", name="uq_agents_tenant_aid"),
    )


class DailyStat(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    total_messages = Column(Integer, nullable=False)
    unique_contacts = Column(Integer, nullable=False)
    conversations = Column(Integer, nullable=False)
    fallback_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "date", name="uq_daily_stats_tenant_date"),
    )


class ChatConversation(Base):
    """Agent conversation sessions from /v1/chat/agent/conversations."""
    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    session_id = Column(String(100), nullable=False)
    conversation_session_id = Column(String(100))
    contact_id = Column(String(100))
    agent_id = Column(String(100))
    agent_email = Column(String(255))
    channel = Column(String(30))
    queued_at = Column(TIMESTAMP(timezone=True))
    assigned_at = Column(TIMESTAMP(timezone=True))
    closed_at = Column(TIMESTAMP(timezone=True))
    initial_session_id = Column(String(100))
    wait_time_seconds = Column(Integer)
    handle_time_seconds = Column(Integer)

    __table_args__ = (
        UniqueConstraint("tenant_id", "session_id", name="uq_chat_conv_tenant_sid"),
        Index("idx_chat_conv_tenant_date", "tenant_id", "closed_at"),
        Index("idx_chat_conv_agent", "tenant_id", "agent_id"),
        Index("idx_chat_conv_contact", "tenant_id", "contact_id"),
    )


class ChatTopic(Base):
    """Conversation topic categories from /v1/chat/topic."""
    __tablename__ = "chat_topics"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    topic_id = Column(String(100), nullable=False)
    topic_name = Column(String(255))
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "topic_id", name="uq_chat_topics_tenant_tid"),
    )


class ChatChannel(Base):
    """WhatsApp / webchat channels from /v1/chat/channel."""
    __tablename__ = "chat_channels"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    channel_id = Column(String(100), nullable=False)
    channel_type = Column(String(30))
    channel_name = Column(String(255))
    phone_number = Column(String(50))
    status = Column(String(20))
    config = Column(JSONB)

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel_id", name="uq_chat_channels_tenant_chid"),
    )


# ============================================================
# Campaigns Domain
# ============================================================

class ToquesDaily(Base):
    __tablename__ = "toques_daily"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    canal = Column(String(30), nullable=False)
    proyecto_cuenta = Column(String(100), nullable=False)
    enviados = Column(Integer, nullable=False, default=0)
    entregados = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    chunks = Column(Integer, nullable=False, default=0)
    usuarios_unicos = Column(Integer, nullable=False, default=0)
    abiertos = Column(Integer)
    rebotes = Column(Integer)
    bloqueados = Column(Integer)
    spam = Column(Integer)
    desuscritos = Column(Integer)
    conversiones = Column(Integer)
    ctr = Column(Numeric(6, 2))
    tasa_entrega = Column(Numeric(6, 2))
    open_rate = Column(Numeric(6, 2))
    conversion_rate = Column(Numeric(6, 2))

    __table_args__ = (
        UniqueConstraint("tenant_id", "date", "canal", "proyecto_cuenta",
                         name="uq_toques_daily_composite"),
        ForeignKeyConstraint(
            ["tenant_id", "date"],
            ["daily_stats.tenant_id", "daily_stats.date"],
            name="fk_toques_daily_daily_stats",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("idx_toques_daily_tenant_date", "tenant_id", "date"),
        Index("idx_toques_daily_canal", "tenant_id", "canal"),
        Index("idx_toques_daily_project", "tenant_id", "proyecto_cuenta"),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    campana_id = Column(String(100), nullable=False)
    campana_nombre = Column(String(255), nullable=False)
    canal = Column(String(30), nullable=False)
    proyecto_cuenta = Column(String(100), nullable=False)
    tipo_campana = Column(String(50))
    total_enviados = Column(Integer, nullable=False, default=0)
    total_entregados = Column(Integer, nullable=False, default=0)
    total_clicks = Column(Integer, nullable=False, default=0)
    total_chunks = Column(Integer, nullable=False, default=0)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    total_abiertos = Column(Integer)
    total_rebotes = Column(Integer)
    total_bloqueados = Column(Integer)
    total_spam = Column(Integer)
    total_desuscritos = Column(Integer)
    total_conversiones = Column(Integer)
    ctr = Column(Numeric(6, 2))
    tasa_entrega = Column(Numeric(6, 2))
    open_rate = Column(Numeric(6, 2))
    conversion_rate = Column(Numeric(6, 2))

    __table_args__ = (
        UniqueConstraint("tenant_id", "campana_id", name="uq_campaigns_tenant_cid"),
    )


class ToquesHeatmap(Base):
    __tablename__ = "toques_heatmap"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    canal = Column(String(30), nullable=False)
    dia_semana = Column(String(12), nullable=False)
    hora = Column(SmallInteger, nullable=False)
    enviados = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    abiertos = Column(Integer)
    conversiones = Column(Integer)
    ctr = Column(Numeric(6, 2))
    dia_orden = Column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "canal", "dia_semana", "hora",
                         name="uq_heatmap_composite"),
    )


class SmsEnvio(Base):
    """Individual SMS sending records imported from console CSV exports."""
    __tablename__ = "sms_envios"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    application_id = Column(String(100), nullable=False)
    campaign_id = Column(String(100), nullable=False)
    campaign_name = Column(String(255))
    sending_id = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=False)
    country_code = Column(String(10))
    external_code = Column(String(100))
    total_chunks = Column(Integer, nullable=False, default=1)
    cost = Column(Numeric(10, 2))
    message_text = Column(Text)
    mcc_mnc = Column(String(20))
    network_name = Column(String(100))
    status = Column(String(30))
    error_description = Column(String(255))
    sending_type = Column(String(30))
    is_flash = Column(Boolean, nullable=False, default=False)
    sent_at = Column(TIMESTAMP(timezone=True))
    clicks = Column(Integer, nullable=False, default=0)
    custom_data = Column(Text)

    __table_args__ = (
        UniqueConstraint("tenant_id", "sending_id", name="uq_sms_envios_tenant_sid"),
        Index("idx_sms_envios_tenant_date", "tenant_id", "sent_at"),
        Index("idx_sms_envios_campaign", "tenant_id", "campaign_id"),
        Index("idx_sms_envios_phone", "tenant_id", "phone"),
        Index("idx_sms_envios_status", "tenant_id", "status"),
    )


class ToquesUsuario(Base):
    __tablename__ = "toques_usuario"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    telefono = Column(String(50), nullable=False)
    canal = Column(String(30), nullable=False)
    proyecto_cuenta = Column(String(100), nullable=False)
    total_toques = Column(Integer, nullable=False)
    total_clicks = Column(Integer, nullable=False)
    primer_toque = Column(Date)
    ultimo_toque = Column(Date)
    dias_activos = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "telefono", "canal", "proyecto_cuenta",
                         name="uq_toques_usuario_composite"),
        Index("idx_toques_usuario_tenant", "tenant_id"),
        Index("idx_toques_usuario_phone", "tenant_id", "telefono"),
    )


# ============================================================
# Application Domain
# ============================================================

class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    query_text = Column(Text, nullable=False)
    ai_function = Column(String(50))
    generated_sql = Column(Text)
    result_data = Column(JSONB, nullable=False)
    result_columns = Column(JSONB, nullable=False)
    result_row_count = Column(Integer, nullable=False)
    visualizations = Column(JSONB, nullable=False, default=[])
    tags = Column(ARRAY(Text))
    is_favorite = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100))
    last_run_at = Column(DateTime(timezone=True))
    conversation_history = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_saved_queries_tenant", "tenant_id"),
        Index("idx_saved_queries_favorite", "tenant_id", "is_favorite",
              postgresql_where=(~Column("is_archived", Boolean))),
    )


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    layout = Column(JSONB, nullable=False, default=[])
    filters = Column(JSONB)
    tags = Column(ARRAY(Text))
    is_favorite = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    auto_refresh_seconds = Column(Integer)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SyncState(Base):
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Text, nullable=False)
    entity = Column(String(50), nullable=False)
    last_cursor = Column(Text)
    last_sync_at = Column(DateTime(timezone=True))
    records_synced = Column(Integer)
    status = Column(String(20), nullable=False, default="pending")

    __table_args__ = (
        UniqueConstraint("tenant_id", "entity", name="uq_sync_state_tenant_entity"),
    )
