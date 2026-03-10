"""Analytics REST API — exposes existing services as JSON endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter

from app.config import settings
from app.routers._utils import sanitize, parse_dates, df_to_response
from app.services.data_service import DataService
from app.services.contact_center_service import ContactCenterService
from app.services.sms_data_service import SmsDataService
from app.services.general_dashboard_service import GeneralDashboardService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── WhatsApp / Bot ───────────────────────────────────────────────

@router.get("/whatsapp/kpis")
async def whatsapp_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_wa_kpis(t, s, e))


@router.get("/whatsapp/summary")
async def whatsapp_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_summary_stats_for_period(t, s, e))


@router.get("/whatsapp/trend")
async def whatsapp_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_messages_over_time_filtered(t, s, e))


@router.get("/whatsapp/by-hour")
async def whatsapp_by_hour(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_hourly_distribution_filtered(t, s, e))


@router.get("/whatsapp/by-direction")
async def whatsapp_by_direction(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_direction_breakdown_filtered(t, s, e))


@router.get("/whatsapp/heatmap")
async def whatsapp_heatmap(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_messages_heatmap(t, s, e))


@router.get("/whatsapp/status")
async def whatsapp_status(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_message_status_distribution(t, s, e))


# ─── Bot ──────────────────────────────────────────────────────────

@router.get("/bot/fallback-trend")
async def bot_fallback_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_fallback_trend_filtered(t, s, e))


@router.get("/bot/intents")
async def bot_intents(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
    limit: int = 10,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_top_intents_filtered(t, s, e, limit))


@router.get("/bot/bot-vs-human")
async def bot_vs_human(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_bot_vs_human_filtered(t, s, e))


@router.get("/bot/resolution")
async def bot_resolution(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_bot_resolution_summary(t, s, e))


@router.get("/bot/content-types")
async def bot_content_types(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_content_type_breakdown(t, s, e))


# ─── Contact Center ──────────────────────────────────────────────

@router.get("/cc/kpis")
async def cc_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_cc_kpis_expanded(t, s, e))


@router.get("/cc/agents")
async def cc_agents(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
    limit: int = 20,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_agent_performance_table(t, s, e, limit))


@router.get("/cc/close-reasons")
async def cc_close_reasons(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_close_reasons(t, s, e))


@router.get("/cc/trend")
async def cc_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_conversations_over_time(t, s, e))


@router.get("/cc/conv-types")
async def cc_conv_types(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_conversation_type_counts(t, s, e))


@router.get("/cc/conv-type-trend")
async def cc_conv_type_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_conversation_type_trend(t, s, e))


@router.get("/cc/frt-trend")
async def cc_frt_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_first_response_time_trend(t, s, e))


@router.get("/cc/handle-trend")
async def cc_handle_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_handle_time_trend(t, s, e))


@router.get("/cc/hourly-queue")
async def cc_hourly_queue(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_hourly_queue(t, s, e))


@router.get("/cc/wait-distribution")
async def cc_wait_distribution(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_wait_time_distribution(t, s, e))


@router.get("/cc/dead-time-trend")
async def cc_dead_time_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = ContactCenterService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_dead_time_trend(t, s, e))


# ─── SMS ──────────────────────────────────────────────────────────

@router.get("/sms/kpis")
async def sms_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_sms_kpis(s, e))


@router.get("/sms/trend")
async def sms_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_sends_vs_chunks_trend(s, e))


@router.get("/sms/clicks-ctr")
async def sms_clicks_ctr(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_sends_clicks_ctr_trend(s, e))


@router.get("/sms/campaigns")
async def sms_campaigns(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_campaign_ranking(s, e, limit))


@router.get("/sms/campaigns-ctr")
async def sms_campaigns_ctr(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_campaign_ranking_by_ctr(s, e, limit))


@router.get("/sms/heatmap")
async def sms_heatmap(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_heatmap_data(s, e))


@router.get("/sms/types")
async def sms_types(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    svc = SmsDataService()
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_sending_type_breakdown(s, e))


# ─── Toques / Control ────────────────────────────────────────────

@router.get("/toques/kpis")
async def toques_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
    threshold: int = 4,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_toques_kpis(t, s, e, threshold))


@router.get("/toques/distribution")
async def toques_distribution(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_toques_distribution(t, s, e))


@router.get("/toques/over-touched")
async def toques_over_touched(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
    threshold: int = 4,
    limit: int = 100,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_over_touched_contacts(t, s, e, threshold, limit))


@router.get("/toques/weekly-trend")
async def toques_weekly_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
    threshold: int = 4,
):
    svc = DataService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_toques_weekly_trend(t, s, e, threshold))


# ─── General / Cross-channel ─────────────────────────────────────

@router.get("/general/kpis")
async def general_kpis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = GeneralDashboardService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return sanitize(svc.get_overview_kpis(t, s, e))


@router.get("/general/channel-summary")
async def general_channel_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = GeneralDashboardService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_channel_summary_table(t, s, e))


@router.get("/general/daily-trend")
async def general_daily_trend(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = GeneralDashboardService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_combined_daily_trend(t, s, e))


@router.get("/general/delivery-funnel")
async def general_delivery_funnel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant: Optional[str] = None,
):
    svc = GeneralDashboardService()
    t = tenant or settings.DEFAULT_TENANT
    s, e = parse_dates(start_date, end_date)
    return df_to_response(svc.get_delivery_funnel(t, s, e))


# ─── Home ─────────────────────────────────────────────────────────

@router.get("/home/stats")
async def home_stats(tenant: Optional[str] = None):
    t = tenant or settings.DEFAULT_TENANT
    data_svc = DataService()
    storage_svc = StorageService(tenant_id=t)

    stats = data_svc.get_summary_stats(t)
    fallback = data_svc.get_fallback_rate(t)
    queries_result = storage_svc.list_queries(limit=5)
    dashboards_result = storage_svc.list_dashboards(limit=5)
    trend_df = data_svc.get_messages_over_time(t)

    trend_data = []
    if trend_df is not None and not trend_df.empty:
        recent = trend_df.tail(30)
        trend_data = recent.to_dict(orient="records")

    return sanitize({
        "total_messages": stats.get("total_messages", 0),
        "total_conversations": stats.get("total_conversations", 0),
        "unique_contacts": stats.get("unique_contacts", 0),
        "active_agents": stats.get("active_agents", 0),
        "fallback_rate": fallback.get("rate", 0),
        "total_queries": queries_result.get("total", 0),
        "total_dashboards": dashboards_result.get("total", 0),
        "recent_queries": queries_result.get("queries", [])[:5],
        "recent_dashboards": dashboards_result.get("dashboards", [])[:5],
        "trend_30d": trend_data,
    })
