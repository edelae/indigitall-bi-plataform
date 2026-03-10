import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare, Bot, Headphones, Send, Shield,
  RefreshCw, Download, Calendar, Loader2,
  Users, Clock, PhoneCall, BarChart3, Zap, AlertTriangle,
  TrendingUp, Hash, Target, ExternalLink,
} from 'lucide-react'
import KpiCard from '../components/KpiCard'
import ChartWidget from '../components/ChartWidget'
import DashboardAnalyst from '../components/DashboardAnalyst'
import { fetchAnalytics, saveQuery } from '../api/client'
import { exportCsv } from '../utils/csvExport'
import type { ChartType } from '../types'

// ─── Types ───────────────────────────────────────────────────────

interface TabData<T> {
  data: T | null
  loading: boolean
  error: string | null
  fetched: boolean
}

interface DfResponse {
  columns: string[]
  data: Record<string, any>[]
}

type TabKey = 'whatsapp' | 'bot' | 'cc' | 'sms' | 'toques'

const TABS: { key: TabKey; label: string; icon: typeof MessageSquare }[] = [
  { key: 'whatsapp', label: 'WhatsApp General', icon: MessageSquare },
  { key: 'bot', label: 'Bot', icon: Bot },
  { key: 'cc', label: 'Contact Center', icon: Headphones },
  { key: 'sms', label: 'SMS', icon: Send },
  { key: 'toques', label: 'Control de Toques', icon: Shield },
]

// ─── Helpers ─────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 0): string {
  if (n === null || n === undefined || isNaN(n)) return '0'
  return Number(n).toLocaleString('es-CO', { maximumFractionDigits: decimals })
}

function fmtPct(n: number | undefined | null): string {
  if (n === null || n === undefined || isNaN(n)) return '0%'
  return `${Number(n).toFixed(1)}%`
}

function fmtTime(seconds: number | undefined | null): string {
  if (!seconds) return '0s'
  const s = Number(seconds)
  if (s < 60) return `${s.toFixed(0)}s`
  if (s < 3600) return `${(s / 60).toFixed(1)}m`
  return `${(s / 3600).toFixed(1)}h`
}

const emptyDf: DfResponse = { columns: [], data: [] }

// ─── Widget wrapper ──────────────────────────────────────────────

function Widget({ title, children, className = '', onExport, onOpenQuery }: {
  title: string; children: React.ReactNode; className?: string;
  onExport?: () => void; onOpenQuery?: () => void
}) {
  return (
    <div className={`card p-4 flex flex-col ${className} ${onOpenQuery ? 'group' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
        <div className="flex items-center gap-1">
          {onOpenQuery && (
            <button
              onClick={onOpenQuery}
              className="opacity-0 group-hover:opacity-100 hover:text-primary transition-all p-1"
              style={{ color: 'var(--text-muted)' }}
              title="Abrir en consultas"
            >
              <ExternalLink size={14} />
            </button>
          )}
          {onExport && (
            <button
              onClick={onExport}
              className="hover:text-primary transition-colors p-1"
              style={{ color: 'var(--text-muted)' }}
              title="Descargar CSV"
            >
              <Download size={14} />
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 min-h-0 cursor-pointer" onClick={onOpenQuery}>{children}</div>
    </div>
  )
}

// ─── Data Table ──────────────────────────────────────────────────

function SimpleTable({ data, columns }: DfResponse) {
  if (!data.length) return <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>Sin datos</p>
  return (
    <div className="overflow-auto max-h-[400px]">
      <table className="w-full text-xs">
        <thead className="sticky top-0" style={{ backgroundColor: 'var(--table-header)' }}>
          <tr>
            {columns.map(c => (
              <th key={c} className="text-left px-2 py-1.5 font-medium" style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}>
                {c.replace(/_/g, ' ').replace(/\b\w/g, x => x.toUpperCase())}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="hover:opacity-80" style={{ borderBottom: '1px solid var(--border-light)' }}>
              {columns.map(c => (
                <td key={c} className="px-2 py-1.5" style={{ color: 'var(--text-primary)' }}>
                  {row[c] !== null && row[c] !== undefined ? String(row[c]) : '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────

export default function DashboardVisionamos() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabKey>('whatsapp')
  const [refreshKey, setRefreshKey] = useState(0)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [threshold, setThreshold] = useState(4)

  // Tab states
  const [wa, setWa] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })
  const [bot, setBot] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })
  const [cc, setCc] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })
  const [sms, setSms] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })
  const [toques, setToques] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })

  const dateParams = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const fetch_ = useCallback(async <T,>(endpoint: string, extra?: Record<string, any>): Promise<T> => {
    return fetchAnalytics<T>(endpoint, { ...dateParams, ...extra })
  }, [startDate, endDate])

  // Reset fetched flags on date change or refresh
  useEffect(() => {
    setWa(s => ({ ...s, fetched: false }))
    setBot(s => ({ ...s, fetched: false }))
    setCc(s => ({ ...s, fetched: false }))
    setSms(s => ({ ...s, fetched: false }))
    setToques(s => ({ ...s, fetched: false }))
  }, [startDate, endDate, refreshKey])

  // ─── WhatsApp tab ────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'whatsapp' || wa.fetched) return
    setWa(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('whatsapp/kpis'),
      fetch_<DfResponse>('whatsapp/trend'),
      fetch_<DfResponse>('whatsapp/by-hour'),
      fetch_<DfResponse>('bot/bot-vs-human'),
      fetch_<DfResponse>('whatsapp/heatmap'),
    ]).then(([kpis, trend, byHour, botHuman, heatmap]) => {
      setWa({ data: { kpis, trend, byHour, botHuman, heatmap }, loading: false, error: null, fetched: true })
    }).catch(e => setWa({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, wa.fetched])

  // ─── Bot tab ─────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'bot' || bot.fetched) return
    setBot(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('whatsapp/kpis'),
      fetch_<DfResponse>('bot/fallback-trend'),
      fetch_<DfResponse>('bot/intents'),
      fetch_<DfResponse>('bot/bot-vs-human'),
      fetch_<DfResponse>('whatsapp/heatmap'),
      fetch_<DfResponse>('bot/content-types'),
    ]).then(([kpis, fallback, intents, botHuman, heatmap, content]) => {
      setBot({ data: { kpis, fallback, intents, botHuman, heatmap, content }, loading: false, error: null, fetched: true })
    }).catch(e => setBot({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, bot.fetched])

  // ─── Contact Center tab ──────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'cc' || cc.fetched) return
    setCc(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('cc/kpis'),
      fetch_<DfResponse>('cc/agents'),
      fetch_<DfResponse>('cc/close-reasons'),
      fetch_<DfResponse>('cc/trend'),
      fetch_<DfResponse>('cc/frt-trend'),
      fetch_<DfResponse>('cc/handle-trend'),
      fetch_<DfResponse>('cc/hourly-queue'),
      fetch_<DfResponse>('cc/conv-type-trend'),
      fetch_<DfResponse>('cc/dead-time-trend'),
      fetch_<DfResponse>('cc/wait-distribution'),
    ]).then(([kpis, agents, reasons, trend, frt, handle, queue, convTypeTrend, deadTime, waitDist]) => {
      setCc({ data: { kpis, agents, reasons, trend, frt, handle, queue, convTypeTrend, deadTime, waitDist }, loading: false, error: null, fetched: true })
    }).catch(e => setCc({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, cc.fetched])

  // ─── SMS tab ─────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'sms' || sms.fetched) return
    setSms(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('sms/kpis'),
      fetch_<DfResponse>('sms/trend'),
      fetch_<DfResponse>('sms/campaigns'),
      fetch_<DfResponse>('sms/campaigns-ctr'),
      fetch_<DfResponse>('sms/heatmap'),
      fetch_<DfResponse>('sms/types'),
    ]).then(([kpis, trend, campaigns, campaignsCtr, heatmap, types]) => {
      setSms({ data: { kpis, trend, campaigns, campaignsCtr, heatmap, types }, loading: false, error: null, fetched: true })
    }).catch(e => setSms({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, sms.fetched])

  // ─── Toques tab ──────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'toques' || toques.fetched) return
    setToques(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('toques/kpis', { threshold }),
      fetch_<DfResponse>('toques/distribution'),
      fetch_<DfResponse>('toques/over-touched', { threshold, limit: 200 }),
      fetch_<DfResponse>('toques/weekly-trend', { threshold }),
    ]).then(([kpis, dist, overTouched, weeklyTrend]) => {
      setToques({ data: { kpis, dist, overTouched, weeklyTrend }, loading: false, error: null, fetched: true })
    }).catch(e => setToques({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, toques.fetched, threshold])

  const currentState = { whatsapp: wa, bot, cc, sms, toques }[activeTab]

  // ─── Render helpers ──────────────────────────────────────────

  function renderLoading() {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-[#0066CC]" size={32} />
        <span className="ml-3 text-[#6B7280]">Cargando datos...</span>
      </div>
    )
  }

  function renderError(msg: string) {
    return (
      <div className="flex items-center justify-center py-20 text-[#EF4444]">
        <AlertTriangle size={20} className="mr-2" />
        <span>{msg}</span>
      </div>
    )
  }

  // SQL queries that back each widget
  const WIDGET_SQL: Record<string, string> = {
    // WhatsApp
    'Mensajes por Hora': `SELECT hour, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY hour\nORDER BY hour`,
    'Distribucion Bot / Humano': `SELECT\n  CASE\n    WHEN is_bot = TRUE THEN 'Bot'\n    WHEN is_human = TRUE THEN 'Agente'\n    WHEN direction = 'Inbound' THEN 'Usuario'\n    ELSE 'Otro'\n  END AS category,\n  COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY category\nORDER BY count DESC`,
    'Tendencia Diaria de Mensajes': `SELECT date, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY date\nORDER BY date`,
    'Heatmap Mensajes por Hora y Dia': `SELECT day_of_week AS dia_semana, hour AS hora, COUNT(*) AS value\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY day_of_week, hour\nORDER BY hour`,
    // Bot
    'Tendencia Tasa Fallback Bot': `SELECT date,\n  COUNT(*) AS total,\n  SUM(CASE WHEN is_fallback = TRUE THEN 1 ELSE 0 END) AS fallback_count,\n  ROUND(SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) AS fallback_rate\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY date\nORDER BY date`,
    'Top Intenciones del Bot': `SELECT intent, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND intent IS NOT NULL AND intent != ''\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY intent\nORDER BY count DESC\nLIMIT 10`,
    'Distribucion Bot vs Humano': `SELECT\n  CASE\n    WHEN is_bot = TRUE THEN 'Bot'\n    WHEN is_human = TRUE THEN 'Agente'\n    WHEN direction = 'Inbound' THEN 'Usuario'\n    ELSE 'Otro'\n  END AS category,\n  COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY category\nORDER BY count DESC`,
    'Tipos de Contenido de Mensajes': `SELECT content_type, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND content_type IS NOT NULL AND content_type != ''\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY content_type\nORDER BY count DESC\nLIMIT 10`,
    'Heatmap Bot Mensajes por Hora y Dia': `SELECT day_of_week AS dia_semana, hour AS hora, COUNT(*) AS value\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY day_of_week, hour\nORDER BY hour`,
    // Contact Center
    'Rendimiento de Agentes Visionamos': `SELECT\n  agent_email AS agente,\n  COUNT(*) AS conversaciones,\n  COUNT(DISTINCT contact_id) AS contactos,\n  AVG(wait_time_seconds) AS avg_frt,\n  AVG(handle_time_seconds) AS avg_handle\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\n  AND agent_email IN (\n    'jmartinez@visionamos.com', 'eamaya@visionamos.com',\n    'jhenao@visionamos.com', 'amarin@visionamos.com',\n    'nmazo@visionamos.com', 'jguerrero@visionamos.com',\n    'vvalencia@visionamos.com', 'acano@visionamos.com',\n    'ypineda@visionamos.com', 'arua@visionamos.com',\n    'vvelez@visionamos.com', 'auribe@visionamos.com',\n    'yzapata@visionamos.com', 'carboleda@visionamos.com',\n    'jurrego@visionamos.com'\n  )\nGROUP BY agent_email\nORDER BY conversaciones DESC`,
    'Razones de Cierre de Conversacion': `SELECT close_reason AS reason, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND close_reason IS NOT NULL AND close_reason != ''\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY close_reason\nORDER BY count DESC`,
    'Conversaciones en el Tiempo': `SELECT date(closed_at) AS date, COUNT(*) AS count\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\nGROUP BY date(closed_at)\nORDER BY date`,
    'Tendencia First Response Time': `SELECT date(closed_at) AS date, AVG(wait_time_seconds) AS avg_frt_seconds\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\n  AND wait_time_seconds IS NOT NULL\nGROUP BY date(closed_at)\nORDER BY date`,
    'Tendencia Handle Time': `SELECT date(closed_at) AS date, AVG(handle_time_seconds) AS avg_handle_seconds\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\n  AND handle_time_seconds IS NOT NULL\nGROUP BY date(closed_at)\nORDER BY date`,
    'Cola de Espera por Hora': `SELECT EXTRACT(HOUR FROM queued_at) AS hour, COUNT(*) AS count\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\n  AND queued_at IS NOT NULL\nGROUP BY hour\nORDER BY hour`,
    'Tipo de Conversacion Bot vs Humano vs Mixta': `WITH conv_flags AS (\n  SELECT conversation_id, MIN(date) AS date,\n    bool_or(is_bot) AS has_bot,\n    bool_or(is_human) AS has_human\n  FROM messages\n  WHERE tenant_id = 'visionamos'\n    AND date >= '${startDate}' AND date <= '${endDate}'\n  GROUP BY conversation_id\n)\nSELECT date,\n  SUM(CASE WHEN has_bot AND NOT has_human THEN 1 ELSE 0 END) AS bot_only,\n  SUM(CASE WHEN NOT has_bot AND has_human THEN 1 ELSE 0 END) AS human_only,\n  SUM(CASE WHEN has_bot AND has_human THEN 1 ELSE 0 END) AS mixed\nFROM conv_flags\nGROUP BY date\nORDER BY date`,
    'Tendencia Dead Time': `SELECT date(closed_at) AS date,\n  AVG(GREATEST(\n    EXTRACT(EPOCH FROM (closed_at - queued_at)) - COALESCE(handle_time_seconds, 0), 0\n  )) AS avg_dead_time_seconds\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND closed_at IS NOT NULL AND queued_at IS NOT NULL\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\nGROUP BY date(closed_at)\nORDER BY date`,
    'Distribucion Tiempo de Espera': `SELECT\n  CASE\n    WHEN wait_time_seconds < 60 THEN '0-1 min'\n    WHEN wait_time_seconds < 300 THEN '1-5 min'\n    WHEN wait_time_seconds < 900 THEN '5-15 min'\n    WHEN wait_time_seconds < 1800 THEN '15-30 min'\n    ELSE '30+ min'\n  END AS bucket,\n  COUNT(*) AS count\nFROM chat_conversations\nWHERE tenant_id = 'visionamos'\n  AND date(closed_at) >= '${startDate}' AND date(closed_at) <= '${endDate}'\n  AND wait_time_seconds IS NOT NULL\nGROUP BY bucket`,
    // SMS
    'SMS Enviados vs Chunks': `SELECT date,\n  COALESCE(SUM(total_sent), 0) AS enviados,\n  COALESCE(SUM(total_chunks), 0) AS chunks\nFROM sms_daily_stats\nWHERE date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY date\nORDER BY date`,
    'Tipo de Envio SMS': `SELECT sending_type, COUNT(*) AS count\nFROM sms_envios\nWHERE date(sent_at) >= '${startDate}' AND date(sent_at) <= '${endDate}'\n  AND sending_type IS NOT NULL\nGROUP BY sending_type\nORDER BY count DESC`,
    'Top Campanas SMS por Volumen': `SELECT campaign_id AS campana, COUNT(*) AS total_enviados,\n  COALESCE(SUM(total_chunks), 0) AS chunks\nFROM sms_envios\nWHERE date(sent_at) >= '${startDate}' AND date(sent_at) <= '${endDate}'\n  AND campaign_id IS NOT NULL\nGROUP BY campaign_id\nORDER BY total_enviados DESC\nLIMIT 10`,
    'Top Campanas SMS por Chunks/Envio': `SELECT campaign_id AS campana, COUNT(*) AS total_enviados,\n  COALESCE(SUM(total_chunks), 0) AS chunks,\n  ROUND(COALESCE(SUM(total_chunks), 0)::numeric / NULLIF(COUNT(*), 0), 2) AS chunks_per_send\nFROM sms_envios\nWHERE date(sent_at) >= '${startDate}' AND date(sent_at) <= '${endDate}'\n  AND campaign_id IS NOT NULL\nGROUP BY campaign_id\nHAVING COUNT(*) > 100\nORDER BY chunks_per_send DESC\nLIMIT 10`,
    'Heatmap SMS por Hora y Dia': `SELECT\n  TO_CHAR(sent_at, 'Day') AS dia_semana,\n  EXTRACT(HOUR FROM sent_at) AS hora,\n  COUNT(*) AS value\nFROM sms_envios\nWHERE date(sent_at) >= '${startDate}' AND date(sent_at) <= '${endDate}'\nGROUP BY dia_semana, hora\nORDER BY hora`,
    // Toques
    'Distribucion de Toques por Contacto': `WITH contact_week AS (\n  SELECT contact_id, TO_CHAR(date, 'IYYY-IW') AS week, COUNT(*) AS msg_count\n  FROM messages\n  WHERE tenant_id = 'visionamos'\n    AND date >= '${startDate}' AND date <= '${endDate}'\n  GROUP BY contact_id, week\n)\nSELECT\n  CASE\n    WHEN msg_count <= 1 THEN '1'\n    WHEN msg_count <= 2 THEN '2'\n    WHEN msg_count <= 3 THEN '3'\n    WHEN msg_count <= 4 THEN '4'\n    WHEN msg_count <= 7 THEN '5-7'\n    WHEN msg_count <= 10 THEN '8-10'\n    ELSE '10+'\n  END AS bucket,\n  COUNT(*) AS count\nFROM contact_week\nGROUP BY bucket`,
    'Tendencia Semanal % Sobre-tocados': `WITH contact_week AS (\n  SELECT contact_id, TO_CHAR(date, 'IYYY-IW') AS week, COUNT(*) AS msg_count\n  FROM messages\n  WHERE tenant_id = 'visionamos'\n    AND date >= '${startDate}' AND date <= '${endDate}'\n  GROUP BY contact_id, week\n)\nSELECT week,\n  COUNT(*) AS total_contacts,\n  SUM(CASE WHEN msg_count > ${threshold} THEN 1 ELSE 0 END) AS over_touched,\n  ROUND(SUM(CASE WHEN msg_count > ${threshold} THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) AS pct_over_touched\nFROM contact_week\nGROUP BY week\nORDER BY week`,
    'Contactos Sobre-tocados': `SELECT contact_id, contact_name,\n  TO_CHAR(date, 'IYYY-IW') AS semana,\n  COUNT(*) AS mensajes\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND date >= '${startDate}' AND date <= '${endDate}'\nGROUP BY contact_id, contact_name, semana\nHAVING COUNT(*) > ${threshold}\nORDER BY semana DESC, mensajes DESC\nLIMIT 100`,
  }

  // Save chart data as query and navigate to consultas
  async function openQuery(title: string, df: DfResponse | undefined, chartType: ChartType) {
    if (!df?.data?.length) return
    try {
      const result = await saveQuery({
        name: title,
        query_text: title,
        data: df.data,
        columns: df.columns,
        chart_type: chartType,
        generated_sql: WIDGET_SQL[title] || null,
        ai_function: 'dashboard_visionamos',
      })
      navigate(`/consultas/nueva?rerun=${result.id}`)
    } catch { /* ignore */ }
  }

  function renderChart(df: DfResponse | undefined, type: ChartType, height = 280) {
    if (!df || !df.data?.length) return <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>Sin datos</p>
    return <ChartWidget data={df.data} columns={df.columns} chartType={type} height={height} />
  }

  // ─── WhatsApp Tab ────────────────────────────────────────────

  function renderWhatsApp() {
    if (!wa.data) return null
    const k = wa.data.kpis
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="card p-1">
            <KpiCard label="Total Mensajes" value={fmt(k.total_messages)} icon={MessageSquare} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Contactos Unicos" value={fmt(k.unique_contacts)} icon={Users} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Tasa Fallback" value={fmtPct(k.fallback_rate)} icon={AlertTriangle} color="#003D73" />
          </div>
          <div className="card p-1">
            <KpiCard label="Tasa Entrega" value={fmtPct(k.delivery_rate)} icon={Target} color="#338FD9" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <Widget title="Mensajes por Hora" className="lg:col-span-3 min-h-[300px]" onOpenQuery={() => openQuery('Mensajes por Hora', wa.data.byHour, 'bar')}>
            {renderChart(wa.data.byHour, 'bar', 260)}
          </Widget>
          <Widget title="Distribucion Bot / Humano" className="lg:col-span-2 min-h-[300px]" onOpenQuery={() => openQuery('Distribucion Bot / Humano', wa.data.botHuman, 'pie')}>
            {renderChart(wa.data.botHuman, 'pie', 260)}
          </Widget>
        </div>
        <Widget title="Tendencia Diaria de Mensajes" className="min-h-[320px]" onOpenQuery={() => openQuery('Tendencia Diaria de Mensajes', wa.data.trend, 'area')}>
          {renderChart(wa.data.trend, 'area', 280)}
        </Widget>
        <Widget title="Heatmap — Mensajes por Hora y Dia" className="min-h-[300px]" onOpenQuery={() => openQuery('Heatmap Mensajes por Hora y Dia', wa.data.heatmap, 'heatmap')}>
          {renderChart(wa.data.heatmap, 'heatmap', 280)}
        </Widget>
      </div>
    )
  }

  // ─── Bot Tab ─────────────────────────────────────────────────

  function renderBot() {
    if (!bot.data) return null
    const k = bot.data.kpis
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="card p-1">
            <KpiCard label="Total Mensajes" value={fmt(k.total_messages)} icon={MessageSquare} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Contactos" value={fmt(k.unique_contacts)} icon={Users} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Tasa Fallback" value={fmtPct(k.fallback_rate)} icon={AlertTriangle} color="#003D73" />
          </div>
          <div className="card p-1">
            <KpiCard label="Resolucion Bot" value={fmtPct(k.bot_resolution_pct)} icon={Bot} color="#338FD9" />
          </div>
          <div className="card p-1">
            <KpiCard label="Espera Promedio" value={fmtTime(k.avg_wait_seconds)} icon={Clock} color="#5AADE0" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Tendencia Tasa Fallback" className="min-h-[300px]" onOpenQuery={() => openQuery('Tendencia Tasa Fallback Bot', bot.data.fallback, 'line')}>
            {renderChart(bot.data.fallback, 'line', 260)}
          </Widget>
          <Widget title="Top Intenciones" className="min-h-[300px]" onOpenQuery={() => openQuery('Top Intenciones del Bot', bot.data.intents, 'bar_horizontal')}>
            {renderChart(bot.data.intents, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Distribucion Bot / Humano" className="min-h-[300px]" onOpenQuery={() => openQuery('Distribucion Bot vs Humano', bot.data.botHuman, 'pie')}>
            {renderChart(bot.data.botHuman, 'pie', 260)}
          </Widget>
          <Widget title="Tipos de Contenido" className="min-h-[300px]" onOpenQuery={() => openQuery('Tipos de Contenido de Mensajes', bot.data.content, 'bar_horizontal')}>
            {renderChart(bot.data.content, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <Widget title="Heatmap — Mensajes por Hora y Dia" className="min-h-[300px]" onOpenQuery={() => openQuery('Heatmap Bot Mensajes por Hora y Dia', bot.data.heatmap, 'heatmap')}>
          {renderChart(bot.data.heatmap, 'heatmap', 280)}
        </Widget>
      </div>
    )
  }

  // ─── Contact Center Tab ──────────────────────────────────────

  function renderCC() {
    if (!cc.data) return null
    const k = cc.data.kpis
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="card p-1">
            <KpiCard label="Conversaciones" value={fmt(k.total_conversations)} icon={PhoneCall} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Agentes Activos" value="15" icon={Users} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="FRT Promedio" value={fmtTime(k.avg_frt_seconds)} icon={Zap} color="#338FD9" />
          </div>
          <div className="card p-1">
            <KpiCard label="Handle Time" value={fmtTime(k.avg_handle_seconds)} icon={Clock} color="#5AADE0" />
          </div>
          <div className="card p-1">
            <KpiCard label="FCR" value={fmtPct(k.fcr_rate)} icon={Target} color="#003D73" />
          </div>
        </div>
        <Widget
          title="Rendimiento de Agentes"
          className="min-h-[200px]"
          onExport={() => cc.data?.agents && exportCsv(cc.data.agents.data, cc.data.agents.columns, 'agentes')}
          onOpenQuery={() => openQuery('Rendimiento de Agentes Visionamos', cc.data.agents, 'table')}
        >
          <SimpleTable {...(cc.data.agents || emptyDf)} />
        </Widget>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Razones de Cierre" className="min-h-[300px]" onOpenQuery={() => openQuery('Razones de Cierre de Conversacion', cc.data.reasons, 'pie')}>
            {renderChart(cc.data.reasons, 'pie', 260)}
          </Widget>
          <Widget title="Conversaciones en el Tiempo" className="min-h-[300px]" onOpenQuery={() => openQuery('Conversaciones en el Tiempo', cc.data.trend, 'area')}>
            {renderChart(cc.data.trend, 'area', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Tendencia FRT" className="min-h-[300px]" onOpenQuery={() => openQuery('Tendencia First Response Time', cc.data.frt, 'line')}>
            {renderChart(cc.data.frt, 'line', 260)}
          </Widget>
          <Widget title="Tendencia Handle Time" className="min-h-[300px]" onOpenQuery={() => openQuery('Tendencia Handle Time', cc.data.handle, 'line')}>
            {renderChart(cc.data.handle, 'line', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Cola por Hora" className="min-h-[300px]" onOpenQuery={() => openQuery('Cola de Espera por Hora', cc.data.queue, 'bar')}>
            {renderChart(cc.data.queue, 'bar', 260)}
          </Widget>
          <Widget title="Tipo Conversacion (Bot/Humano/Mixta)" className="min-h-[300px]" onOpenQuery={() => openQuery('Tipo de Conversacion Bot vs Humano vs Mixta', cc.data.convTypeTrend, 'area_stacked')}>
            {renderChart(cc.data.convTypeTrend, 'area_stacked', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Tendencia Dead Time" className="min-h-[300px]" onOpenQuery={() => openQuery('Tendencia Dead Time', cc.data.deadTime, 'line')}>
            {renderChart(cc.data.deadTime, 'line', 260)}
          </Widget>
          <Widget title="Distribucion Tiempo de Espera" className="min-h-[300px]" onOpenQuery={() => openQuery('Distribucion Tiempo de Espera', cc.data.waitDist, 'bar')}>
            {renderChart(cc.data.waitDist, 'bar', 260)}
          </Widget>
        </div>
      </div>
    )
  }

  // ─── SMS Tab ─────────────────────────────────────────────────

  function renderSMS() {
    if (!sms.data) return null
    const k = sms.data.kpis
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="card p-1">
            <KpiCard label="Enviados" value={fmt(k.total_enviados)} icon={Send} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Total Chunks" value={fmt(k.total_chunks)} icon={Hash} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Entregados" value={fmt(k.total_delivered)} icon={BarChart3} color="#338FD9" />
          </div>
          <div className="card p-1">
            <KpiCard label="Clicks" value={fmt(k.total_clicks)} icon={Target} color="#5AADE0" />
          </div>
          <div className="card p-1">
            <KpiCard label="Campanas" value={fmt(k.campanas)} icon={BarChart3} color="#003D73" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Enviados vs Chunks" className="min-h-[300px]" onOpenQuery={() => openQuery('SMS Enviados vs Chunks', sms.data.trend, 'line')}>
            {renderChart(sms.data.trend, 'line', 260)}
          </Widget>
          <Widget title="Tipo de Envio" className="min-h-[300px]" onOpenQuery={() => openQuery('Tipo de Envio SMS', sms.data.types, 'pie')}>
            {renderChart(sms.data.types, 'pie', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Top Campanas por Volumen" className="min-h-[300px]" onOpenQuery={() => openQuery('Top Campanas SMS por Volumen', sms.data.campaigns, 'bar_horizontal')}>
            {renderChart(sms.data.campaigns, 'bar_horizontal', 260)}
          </Widget>
          <Widget title="Top Campanas por Chunks/Envio" className="min-h-[300px]" onOpenQuery={() => openQuery('Top Campanas SMS por Chunks/Envio', sms.data.campaignsCtr, 'bar_horizontal')}>
            {renderChart(sms.data.campaignsCtr, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <Widget title="Heatmap — SMS por Hora y Dia" className="min-h-[300px]" onOpenQuery={() => openQuery('Heatmap SMS por Hora y Dia', sms.data.heatmap, 'heatmap')}>
          {renderChart(sms.data.heatmap, 'heatmap', 280)}
        </Widget>
      </div>
    )
  }

  // ─── Toques Tab ──────────────────────────────────────────────

  function renderToques() {
    if (!toques.data) return null
    const k = toques.data.kpis
    return (
      <div className="space-y-3">
        {/* Threshold slider */}
        <div className="card p-4">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Umbral de sobre-toque:
            </label>
            <input
              type="range" min={1} max={10} value={threshold}
              onChange={e => { setThreshold(Number(e.target.value)); setToques(s => ({ ...s, fetched: false })) }}
              className="flex-1 max-w-[200px] accent-primary"
            />
            <span className="text-sm font-bold text-primary w-6">{threshold}</span>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>mensajes/contacto/semana</span>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="card p-1">
            <KpiCard label="% Sobre-tocados" value={fmtPct(k.pct_over_touched)} icon={AlertTriangle} color="#003D73" />
          </div>
          <div className="card p-1">
            <KpiCard label="Contacto-Semanas" value={fmt(k.total_contact_weeks)} icon={Users} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Sobre-tocados" value={fmt(k.over_touched)} icon={Shield} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Prom. Msgs/Contacto" value={fmt(k.avg_msgs_per_contact_week, 1)} icon={TrendingUp} color="#338FD9" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Distribucion de Toques por Contacto" className="min-h-[300px]" onOpenQuery={() => openQuery('Distribucion de Toques por Contacto', toques.data.dist, 'bar')}>
            {renderChart(toques.data.dist, 'bar', 260)}
          </Widget>
          <Widget title="Tendencia Semanal % Sobre-tocados" className="min-h-[300px]" onOpenQuery={() => openQuery('Tendencia Semanal % Sobre-tocados', toques.data.weeklyTrend, 'line')}>
            {renderChart(toques.data.weeklyTrend, 'line', 260)}
          </Widget>
        </div>

        <Widget
          title="Contactos Sobre-tocados"
          className="min-h-[200px]"
          onExport={() => toques.data?.overTouched && exportCsv(toques.data.overTouched.data, toques.data.overTouched.columns, 'sobre_tocados')}
          onOpenQuery={() => openQuery('Contactos Sobre-tocados', toques.data.overTouched, 'table')}
        >
          <SimpleTable {...(toques.data.overTouched || emptyDf)} />
        </Widget>
      </div>
    )
  }

  // ─── Main render ─────────────────────────────────────────────

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    whatsapp: renderWhatsApp,
    bot: renderBot,
    cc: renderCC,
    sms: renderSMS,
    toques: renderToques,
  }

  return (
    <div className="animate-fade-in -mx-6 -my-6">
      {/* Canvas background */}
      <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
        {/* Header */}
        <div className="px-6 py-4" style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
          <div className="max-w-[1400px] mx-auto flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Dashboard Visionamos</h1>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>WhatsApp + Contact Center + SMS — Datos en tiempo real</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Calendar size={14} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="date" value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="input text-xs !w-auto !px-2 !py-1"
                />
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>—</span>
                <input
                  type="date" value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="input text-xs !w-auto !px-2 !py-1"
                />
              </div>
              <button
                onClick={() => setRefreshKey(k => k + 1)}
                className="btn-primary flex items-center gap-1 text-xs px-3 py-1.5"
              >
                <RefreshCw size={12} />
                Actualizar
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
          <div className="max-w-[1400px] mx-auto px-6 flex gap-0 overflow-x-auto">
            {TABS.map(tab => {
              const Icon = tab.icon
              const isActive = activeTab === tab.key
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    isActive
                      ? 'border-primary text-primary'
                      : 'border-transparent hover:border-border'
                  }`}
                  style={!isActive ? { color: 'var(--text-secondary)' } : {}}
                >
                  <Icon size={15} />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="max-w-[1400px] mx-auto px-6 py-4">
          {currentState.loading && renderLoading()}
          {currentState.error && !currentState.loading && renderError(currentState.error)}
          {!currentState.loading && !currentState.error && currentState.data && tabContent[activeTab]()}
          {!currentState.loading && !currentState.error && !currentState.data && !currentState.fetched && renderLoading()}
        </div>
      </div>

      {/* AI Analyst Panel */}
      <DashboardAnalyst
        context={{
          activeTab,
          kpis: collectKpis(),
          dateRange: startDate && endDate ? { start: startDate, end: endDate } : undefined,
        }}
      />
    </div>
  )

  function collectKpis(): Record<string, string | number> {
    const kpis: Record<string, string | number> = {}
    const tabData = { whatsapp: wa, bot, cc, sms, toques }[activeTab]
    if (!tabData?.data?.kpis) return kpis
    const k = tabData.data.kpis
    for (const [key, val] of Object.entries(k)) {
      if (val !== null && val !== undefined) {
        kpis[key] = val as string | number
      }
    }
    return kpis
  }
}
