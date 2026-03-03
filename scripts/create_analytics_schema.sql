-- ═══════════════════════════════════════════════════════════════════════
-- DDL Migration: Create analytics star schema
-- Run this BEFORE dbt run to create the schema.
-- dbt will create tables within public_analytics schema via +schema: analytics.
--
-- Usage:
--   psql -h <host> -U postgres -d postgres -f scripts/create_analytics_schema.sql
-- ═══════════════════════════════════════════════════════════════════════

-- Create schema (dbt uses public_analytics convention)
CREATE SCHEMA IF NOT EXISTS public_analytics;

-- ═══════════════════════════════════════════
-- Post-dbt indexes (run AFTER dbt run)
-- dbt creates the tables; this script adds performance indexes.
-- ═══════════════════════════════════════════

-- dim_date
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_date_full_date
    ON public_analytics.dim_date (full_date);

CREATE INDEX IF NOT EXISTS idx_dim_date_year_month
    ON public_analytics.dim_date (year_month);

-- dim_channel
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_channel_code
    ON public_analytics.dim_channel (channel_code);

-- dim_event_type
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_event_type_code
    ON public_analytics.dim_event_type (event_code);

-- dim_contact
CREATE INDEX IF NOT EXISTS idx_dim_contact_tenant
    ON public_analytics.dim_contact (tenant_id);

CREATE INDEX IF NOT EXISTS idx_dim_contact_tenant_phone
    ON public_analytics.dim_contact (tenant_id, phone)
    WHERE phone IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dim_contact_tenant_cid
    ON public_analytics.dim_contact (tenant_id, contact_id)
    WHERE contact_id IS NOT NULL;

-- dim_agent
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_agent_tenant_aid
    ON public_analytics.dim_agent (tenant_id, agent_id);

-- dim_campaign
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_campaign_tenant_cid
    ON public_analytics.dim_campaign (tenant_id, campaign_id);

-- dim_conversation
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_conversation_tenant_cid
    ON public_analytics.dim_conversation (tenant_id, conversation_id);

CREATE INDEX IF NOT EXISTS idx_dim_conversation_contact
    ON public_analytics.dim_conversation (contact_key)
    WHERE contact_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dim_conversation_agent
    ON public_analytics.dim_conversation (agent_key)
    WHERE agent_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dim_conversation_closed
    ON public_analytics.dim_conversation (tenant_id, closed_at);

-- ═══════════════════════════════════════════
-- fact_message_events indexes
-- ═══════════════════════════════════════════

-- Primary filter: date range + channel
CREATE INDEX IF NOT EXISTS idx_fact_events_date_channel
    ON public_analytics.fact_message_events (date_key, channel_key);

-- KPI aggregations (delivery rate, CTR)
CREATE INDEX IF NOT EXISTS idx_fact_events_channel_event_date
    ON public_analytics.fact_message_events (channel_key, event_type_key, date_key);

-- Tenant isolation
CREATE INDEX IF NOT EXISTS idx_fact_events_tenant_date
    ON public_analytics.fact_message_events (tenant_key, date_key);

-- Campaign performance (partial: only rows with campaign)
CREATE INDEX IF NOT EXISTS idx_fact_events_campaign
    ON public_analytics.fact_message_events (campaign_key, event_type_key)
    WHERE campaign_key IS NOT NULL;

-- Conversation drill-down (partial: only rows with conversation)
CREATE INDEX IF NOT EXISTS idx_fact_events_conversation
    ON public_analytics.fact_message_events (conversation_key)
    WHERE conversation_key IS NOT NULL;

-- Contact activity (partial: only rows with contact)
CREATE INDEX IF NOT EXISTS idx_fact_events_contact_date
    ON public_analytics.fact_message_events (contact_key, date_key)
    WHERE contact_key IS NOT NULL;

-- Agent performance (partial: only rows with agent)
CREATE INDEX IF NOT EXISTS idx_fact_events_agent_date
    ON public_analytics.fact_message_events (agent_key, date_key)
    WHERE agent_key IS NOT NULL;

-- Fallback analysis (partial: only fallback rows)
CREATE INDEX IF NOT EXISTS idx_fact_events_fallback
    ON public_analytics.fact_message_events (date_key)
    WHERE is_fallback = true;
