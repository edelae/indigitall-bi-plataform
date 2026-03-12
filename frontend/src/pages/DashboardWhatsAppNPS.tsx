import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare, Bot, RefreshCw, Download, Calendar, Loader2,
  Users, AlertTriangle, TrendingUp, Target, ExternalLink,
  ThumbsUp, ThumbsDown, Star, BarChart3, Minus, Pencil,
} from 'lucide-react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Cell,
} from 'recharts'
import KpiCard from '../components/KpiCard'
import ChartWidget from '../components/ChartWidget'
import DashboardAnalyst from '../components/DashboardAnalyst'
import { fetchAnalytics, saveQuery, saveDashboard } from '../api/client'
import { exportCsv } from '../utils/csvExport'
import type { ChartType, DashboardWidget } from '../types'

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

type TabKey = 'general' | 'bot'
type PeriodKey = 'month' | 'week' | 'day'

const TABS: { key: TabKey; label: string; icon: typeof MessageSquare }[] = [
  { key: 'general', label: 'WhatsApp General', icon: MessageSquare },
  { key: 'bot', label: 'WhatsApp BOT', icon: Bot },
]

// Monochromatic blue palette
const BLUE_PALETTE = {
  bot: '#0066CC',
  agente: '#338FD9',
  mixta: '#80C4E8',
  botLine: '#003D73',
  agenteLine: '#0052A3',
  mixtaline: '#5AADE0',
  totalLine: '#002B54',
  fallback: '#0066CC',
  fallbackRate: '#003D73',
}

// ─── Helpers ─────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 0): string {
  if (n === null || n === undefined || isNaN(n)) return '0'
  return Number(n).toLocaleString('es-CO', { maximumFractionDigits: decimals })
}

function fmtPct(n: number | undefined | null): string {
  if (n === null || n === undefined || isNaN(n)) return '0%'
  return `${Number(n).toFixed(1)}%`
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

// ─── Simple Table ────────────────────────────────────────────────

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

// ─── Period Selector ─────────────────────────────────────────────

function PeriodSelector({ value, onChange }: { value: PeriodKey; onChange: (v: PeriodKey) => void }) {
  const opts: { key: PeriodKey; label: string }[] = [
    { key: 'month', label: 'Mensual' },
    { key: 'week', label: 'Semanal' },
    { key: 'day', label: 'Diario' },
  ]
  return (
    <div className="flex gap-1 bg-surface rounded-btn p-0.5">
      {opts.map(o => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className={`px-3 py-1 text-xs rounded-btn transition-colors ${
            value === o.key
              ? 'bg-primary text-white font-medium'
              : 'hover:bg-border'
          }`}
          style={value !== o.key ? { color: 'var(--text-secondary)' } : {}}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// ─── Custom Dual-Axis NPS Chart ──────────────────────────────────

function NpsCanalChart({ data }: { data: Record<string, any>[] }) {
  if (!data.length) return <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>Sin datos</p>

  const tooltipStyle = {
    contentStyle: {
      backgroundColor: '#1A1A2E',
      border: 'none',
      borderRadius: '8px',
      fontSize: '12px',
      color: '#D1D5DB',
      fontFamily: 'Inter',
    },
    labelStyle: { color: '#9CA3AF', fontWeight: 600, marginBottom: 4 },
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
        <XAxis
          dataKey="periodo"
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={{ stroke: '#E4E4E7' }}
        />
        <YAxis
          yAxisId="left"
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={false}
          label={{ value: 'Encuestas', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#9CA3AF' } }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[-100, 100]}
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={false}
          label={{ value: 'NPS Score', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#9CA3AF' } }}
        />
        <Tooltip {...tooltipStyle} />
        <Legend
          wrapperStyle={{ fontSize: '11px', fontFamily: 'Inter', paddingTop: 8 }}
        />
        {/* Bars for counts */}
        <Bar yAxisId="left" dataKey="agente_count" name="Agente" fill={BLUE_PALETTE.agente} radius={[3, 3, 0, 0]} stackId="canal" />
        <Bar yAxisId="left" dataKey="mixta_count" name="Mixta" fill={BLUE_PALETTE.mixta} radius={[3, 3, 0, 0]} stackId="canal" />
        <Bar yAxisId="left" dataKey="bot_count" name="Bot" fill={BLUE_PALETTE.bot} radius={[3, 3, 0, 0]} stackId="canal" />
        {/* Lines for NPS */}
        <Line yAxisId="right" type="monotone" dataKey="agente_nps" name="NPS Agente" stroke={BLUE_PALETTE.agenteLine} strokeWidth={2.5} dot={{ fill: BLUE_PALETTE.agenteLine, r: 3 }} />
        <Line yAxisId="right" type="monotone" dataKey="mixta_nps" name="NPS Mixta" stroke={BLUE_PALETTE.mixtaline} strokeWidth={2.5} dot={{ fill: BLUE_PALETTE.mixtaline, r: 3 }} strokeDasharray="4 4" />
        <Line yAxisId="right" type="monotone" dataKey="bot_nps" name="NPS Bot" stroke={BLUE_PALETTE.botLine} strokeWidth={2.5} dot={{ fill: BLUE_PALETTE.botLine, r: 3 }} />
        <Line yAxisId="right" type="monotone" dataKey="total_nps" name="NPS Total" stroke={BLUE_PALETTE.totalLine} strokeWidth={3} dot={{ fill: BLUE_PALETTE.totalLine, r: 4 }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

// ─── Custom Fallback Trend Chart ─────────────────────────────────

function FallbackTrendChart({ data }: { data: Record<string, any>[] }) {
  if (!data.length) return <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>Sin datos</p>

  const tooltipStyle = {
    contentStyle: {
      backgroundColor: '#1A1A2E',
      border: 'none',
      borderRadius: '8px',
      fontSize: '12px',
      color: '#D1D5DB',
      fontFamily: 'Inter',
    },
    labelStyle: { color: '#9CA3AF', fontWeight: 600, marginBottom: 4 },
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
        <XAxis
          dataKey="periodo"
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={{ stroke: '#E4E4E7' }}
        />
        <YAxis
          yAxisId="left"
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={false}
          label={{ value: 'Fallbacks', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#9CA3AF' } }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          domain={[0, 'auto']}
          tick={{ fontSize: 11, fill: '#6E7191', fontFamily: 'Inter' }}
          tickLine={false}
          axisLine={false}
          label={{ value: 'Tasa %', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#9CA3AF' } }}
        />
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'Inter', paddingTop: 8 }} />
        <Bar yAxisId="left" dataKey="fallbacks" name="Fallbacks" fill={BLUE_PALETTE.fallback} radius={[4, 4, 0, 0]} />
        <Line yAxisId="right" type="monotone" dataKey="fallback_rate" name="Tasa Fallback %" stroke={BLUE_PALETTE.fallbackRate} strokeWidth={2.5} dot={{ fill: BLUE_PALETTE.fallbackRate, r: 3 }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

// ─── Main Component ──────────────────────────────────────────────

export default function DashboardWhatsAppNPS() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabKey>('general')
  const [refreshKey, setRefreshKey] = useState(0)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [npsPeriod, setNpsPeriod] = useState<PeriodKey>('month')
  const [fallbackPeriod, setFallbackPeriod] = useState<PeriodKey>('month')

  // Tab states
  const [general, setGeneral] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })
  const [botTab, setBotTab] = useState<TabData<any>>({ data: null, loading: false, error: null, fetched: false })

  const dateParams = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const fetch_ = useCallback(async <T,>(endpoint: string, extra?: Record<string, any>): Promise<T> => {
    return fetchAnalytics<T>(endpoint, { ...dateParams, ...extra })
  }, [startDate, endDate])

  // Reset on date/refresh change
  useEffect(() => {
    setGeneral(s => ({ ...s, fetched: false }))
    setBotTab(s => ({ ...s, fetched: false }))
  }, [startDate, endDate, refreshKey])

  // ─── WhatsApp General tab ──────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'general' || general.fetched) return
    setGeneral(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('nps/kpis'),
      fetch_<DfResponse>('nps/trend', { period: npsPeriod }),
      fetch_<DfResponse>('nps/by-entity'),
      fetch_<DfResponse>('nps/distribution'),
      fetch_<DfResponse>('nps/intent-vs-canal'),
    ]).then(([kpis, trend, byEntity, distribution, intentCanal]) => {
      setGeneral({ data: { kpis, trend, byEntity, distribution, intentCanal }, loading: false, error: null, fetched: true })
    }).catch(e => setGeneral({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, general.fetched])

  // Refetch NPS trend when period changes
  useEffect(() => {
    if (activeTab !== 'general' || !general.data) return
    fetch_<DfResponse>('nps/trend', { period: npsPeriod })
      .then(trend => setGeneral(s => s.data ? { ...s, data: { ...s.data, trend } } : s))
      .catch(() => {})
  }, [npsPeriod])

  // ─── WhatsApp BOT tab ──────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'bot' || botTab.fetched) return
    setBotTab(s => ({ ...s, loading: true, error: null }))
    Promise.all([
      fetch_<any>('nps/bot-kpis'),
      fetch_<DfResponse>('nps/fallback-trend', { period: fallbackPeriod }),
      fetch_<DfResponse>('nps/fallback-by-intent'),
      fetch_<DfResponse>('bot/intents'),
    ]).then(([kpis, fallbackTrend, fallbackIntent, topIntents]) => {
      setBotTab({ data: { kpis, fallbackTrend, fallbackIntent, topIntents }, loading: false, error: null, fetched: true })
    }).catch(e => setBotTab({ data: null, loading: false, error: e.message, fetched: true }))
  }, [activeTab, botTab.fetched])

  // Refetch fallback trend when period changes
  useEffect(() => {
    if (activeTab !== 'bot' || !botTab.data) return
    fetch_<DfResponse>('nps/fallback-trend', { period: fallbackPeriod })
      .then(fallbackTrend => setBotTab(s => s.data ? { ...s, data: { ...s.data, fallbackTrend } } : s))
      .catch(() => {})
  }, [fallbackPeriod])

  const currentState = activeTab === 'general' ? general : botTab

  // ─── Clone as editable dashboard ─────────────────────────────

  async function handleEditDashboard() {
    const widgets: DashboardWidget[] = []
    const tabDefs = [
      { tabKey: 'general', tabName: 'WhatsApp General', data: general.data, items: [
        { title: 'NPS vs Canal', dataKey: 'trend', chartType: 'combo' as ChartType, w: 12, h: 5 },
        { title: 'Distribucion NPS', dataKey: 'distribution', chartType: 'pie' as ChartType, w: 5, h: 4 },
        { title: 'NPS por Entidad', dataKey: 'byEntity', chartType: 'bar_horizontal' as ChartType, w: 7, h: 4 },
        { title: 'Intent vs Canal', dataKey: 'intentCanal', chartType: 'bar_stacked' as ChartType, w: 12, h: 4 },
      ]},
      { tabKey: 'bot', tabName: 'WhatsApp BOT', data: botTab.data, items: [
        { title: 'Tendencia Fallbacks', dataKey: 'fallbackTrend', chartType: 'combo' as ChartType, w: 12, h: 5 },
        { title: 'Fallbacks por Intent', dataKey: 'fallbackIntent', chartType: 'bar_horizontal' as ChartType, w: 6, h: 4 },
        { title: 'Top Intenciones Bot', dataKey: 'topIntents', chartType: 'bar_horizontal' as ChartType, w: 6, h: 4 },
      ]},
    ]

    for (const tab of tabDefs) {
      if (!tab.data) continue
      let y = 0
      let colIdx = 0
      for (const item of tab.items) {
        const df = tab.data[item.dataKey]
        if (!df?.data?.length) continue
        const x = item.w >= 12 ? 0 : (colIdx % 2) * 6
        widgets.push({
          grid_i: `${tab.tabKey}-${item.dataKey}`,
          grid_x: x,
          grid_y: y,
          grid_w: item.w,
          grid_h: item.h,
          title: item.title,
          type: item.chartType,
          chart_type: item.chartType,
          width: item.w,
          data: df.data,
          columns: df.columns,
          sql: WIDGET_SQL[item.title] || undefined,
          query_text: item.title,
          tab_id: tab.tabKey,
          tab_name: tab.tabName,
        })
        colIdx++
        if (item.w >= 12 || colIdx % 2 === 0) y += item.h
      }
    }

    try {
      const result = await saveDashboard({
        name: 'WhatsApp NPS & Bot (Editable)',
        description: 'Copia editable del dashboard WhatsApp Analytics NPS & Bot',
        layout: widgets,
      })
      navigate(`/tableros/nuevo?edit=${result.id}`)
    } catch (e: any) {
      alert('Error al crear dashboard editable: ' + (e.message || 'Error desconocido'))
    }
  }

  // ─── WIDGET_SQL ────────────────────────────────────────────

  const WIDGET_SQL: Record<string, string> = {
    'NPS vs Canal': `SELECT\n  month_label AS periodo,\n  canal_tipo,\n  COUNT(*) AS encuestas,\n  SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END) AS promotores,\n  SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END) AS detractores,\n  ROUND(\n    (SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END)\n     - SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END))::numeric\n    / NULLIF(COUNT(*), 0) * 100, 1\n  ) AS nps_score\nFROM nps_surveys\nWHERE tenant_id = 'visionamos'\nGROUP BY month_label, canal_tipo\nORDER BY month_label, canal_tipo`,
    'NPS por Entidad': `SELECT\n  entity AS entidad,\n  COUNT(*) AS encuestas,\n  ROUND(AVG(score_atencion)::numeric, 2) AS avg_atencion,\n  ROUND(AVG(score_asesor)::numeric, 2) AS avg_asesor,\n  ROUND(\n    (SUM(CASE WHEN nps_categoria = 'Promotor' THEN 1 ELSE 0 END)\n     - SUM(CASE WHEN nps_categoria = 'Detractor' THEN 1 ELSE 0 END))::numeric\n    / NULLIF(COUNT(*), 0) * 100, 1\n  ) AS nps_score\nFROM nps_surveys\nWHERE entity IS NOT NULL AND entity != ''\nGROUP BY entity\nORDER BY encuestas DESC`,
    'Distribucion NPS': `SELECT nps_categoria AS categoria, COUNT(*) AS count\nFROM nps_surveys\nWHERE tenant_id = 'visionamos'\n  AND nps_categoria IS NOT NULL\nGROUP BY nps_categoria\nORDER BY count DESC`,
    'Intent vs Canal': `WITH conv_types AS (\n  SELECT conversation_id,\n    CASE\n      WHEN bool_or(is_bot) AND bool_or(is_human) THEN 'Mixta'\n      WHEN bool_or(is_human) THEN 'Agente'\n      WHEN bool_or(is_bot) THEN 'Bot'\n      ELSE 'Otro'\n    END AS canal_tipo\n  FROM messages\n  WHERE tenant_id = 'visionamos'\n  GROUP BY conversation_id\n)\nSELECT m.intent, ct.canal_tipo, COUNT(*) AS count\nFROM messages m\nLEFT JOIN conv_types ct ON m.conversation_id = ct.conversation_id\nWHERE m.intent IS NOT NULL AND m.intent != ''\n  AND m.tenant_id = 'visionamos'\nGROUP BY m.intent, ct.canal_tipo\nORDER BY m.intent`,
    'Tendencia Fallbacks': `WITH conv_flags AS (\n  SELECT conversation_id, MIN(date) AS date,\n    BOOL_OR(is_fallback) AS had_fallback,\n    BOOL_OR(is_bot) AS had_bot\n  FROM messages\n  WHERE tenant_id = 'visionamos'\n    AND conversation_id IS NOT NULL\n  GROUP BY conversation_id\n)\nSELECT TO_CHAR(date, 'YYYY-MM') AS periodo,\n  COUNT(*) FILTER (WHERE had_bot) AS total_bot_convs,\n  COUNT(*) FILTER (WHERE had_bot AND had_fallback) AS fallbacks,\n  ROUND(COUNT(*) FILTER (WHERE had_bot AND had_fallback)::numeric\n    / NULLIF(COUNT(*) FILTER (WHERE had_bot), 0) * 100, 1) AS fallback_rate\nFROM conv_flags\nGROUP BY TO_CHAR(date, 'YYYY-MM')\nORDER BY periodo`,
    'Fallbacks por Intent': `WITH conv_intents AS (\n  SELECT conversation_id, intent,\n    BOOL_OR(is_fallback) AS had_fallback\n  FROM messages\n  WHERE is_bot = TRUE AND tenant_id = 'visionamos'\n    AND conversation_id IS NOT NULL\n  GROUP BY conversation_id, intent\n)\nSELECT COALESCE(intent, 'Sin Intent') AS intent,\n  COUNT(*) AS total,\n  SUM(CASE WHEN had_fallback THEN 1 ELSE 0 END) AS fallbacks,\n  ROUND(SUM(CASE WHEN had_fallback THEN 1 ELSE 0 END)::numeric\n    / NULLIF(COUNT(*), 0) * 100, 1) AS fallback_rate\nFROM conv_intents\nGROUP BY intent\nHAVING SUM(CASE WHEN had_fallback THEN 1 ELSE 0 END) > 0\nORDER BY fallbacks DESC\nLIMIT 15`,
    'Top Intenciones Bot': `SELECT intent, COUNT(*) AS count\nFROM messages\nWHERE tenant_id = 'visionamos'\n  AND intent IS NOT NULL AND intent != ''\nGROUP BY intent\nORDER BY count DESC\nLIMIT 10`,
  }

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
        ai_function: 'dashboard_whatsapp_nps',
      })
      navigate(`/consultas/nueva?rerun=${result.id}`)
    } catch { /* ignore */ }
  }

  function renderChart(df: DfResponse | undefined, type: ChartType, height = 280) {
    if (!df || !df.data?.length) return <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>Sin datos</p>
    return <ChartWidget data={df.data} columns={df.columns} chartType={type} height={height} />
  }

  // ─── Render Helpers ────────────────────────────────────────

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

  // ─── WhatsApp General Tab ──────────────────────────────────

  function renderGeneral() {
    if (!general.data) return null
    const k = general.data.kpis

    return (
      <div className="space-y-3">
        {/* KPI Row */}
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
          <div className="card p-1">
            <KpiCard label="Encuestas" value={fmt(k.total_surveys)} icon={Star} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="NPS Score" value={fmt(k.nps_score, 1)} icon={TrendingUp} color="#003D73" />
          </div>
          <div className="card p-1">
            <KpiCard label="Promotores" value={fmtPct(k.pct_promotores)} icon={ThumbsUp} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Detractores" value={fmtPct(k.pct_detractores)} icon={ThumbsDown} color="#338FD9" />
          </div>
          <div className="card p-1">
            <KpiCard label="Avg Atencion" value={fmt(k.avg_score_atencion, 2)} icon={Target} color="#5AADE0" />
          </div>
          <div className="card p-1">
            <KpiCard label="Entidades" value={fmt(k.entidades)} icon={Users} color="#80C4E8" />
          </div>
        </div>

        {/* NPS vs Canal — main chart */}
        <Widget
          title="NPS vs Canal"
          className="min-h-[360px]"
          onOpenQuery={() => openQuery('NPS vs Canal', general.data.trend, 'combo')}
          onExport={() => general.data?.trend && exportCsv(general.data.trend.data, general.data.trend.columns, 'nps_vs_canal')}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Barras = Cantidad de encuestas por canal &middot; Lineas = NPS Score por canal
            </p>
            <PeriodSelector value={npsPeriod} onChange={v => setNpsPeriod(v)} />
          </div>
          <NpsCanalChart data={general.data.trend?.data || []} />
        </Widget>

        {/* NPS Distribution + NPS by Entity */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <Widget
            title="Distribucion NPS"
            className="lg:col-span-2 min-h-[300px]"
            onOpenQuery={() => openQuery('Distribucion NPS', general.data.distribution, 'pie')}
          >
            {renderChart(general.data.distribution, 'pie', 260)}
          </Widget>
          <Widget
            title="NPS por Entidad"
            className="lg:col-span-3 min-h-[300px]"
            onOpenQuery={() => openQuery('NPS por Entidad', general.data.byEntity, 'bar_horizontal')}
            onExport={() => general.data?.byEntity && exportCsv(general.data.byEntity.data, general.data.byEntity.columns, 'nps_por_entidad')}
          >
            {renderChart(general.data.byEntity, 'bar_horizontal', 260)}
          </Widget>
        </div>

        {/* Intent vs Canal */}
        <Widget
          title="Intent vs Canal"
          className="min-h-[300px]"
          onOpenQuery={() => openQuery('Intent vs Canal', general.data.intentCanal, 'bar_stacked')}
          onExport={() => general.data?.intentCanal && exportCsv(general.data.intentCanal.data, general.data.intentCanal.columns, 'intent_vs_canal')}
        >
          {renderChart(general.data.intentCanal, 'bar_stacked', 260)}
        </Widget>
      </div>
    )
  }

  // ─── WhatsApp BOT Tab ──────────────────────────────────────

  function renderBot() {
    if (!botTab.data) return null
    const k = botTab.data.kpis

    return (
      <div className="space-y-3">
        {/* KPI Row */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="card p-1">
            <KpiCard label="Mensajes Bot" value={fmt(k.total_bot_messages)} icon={Bot} color="#0066CC" />
          </div>
          <div className="card p-1">
            <KpiCard label="Contactos" value={fmt(k.unique_contacts)} icon={Users} color="#0052A3" />
          </div>
          <div className="card p-1">
            <KpiCard label="Intenciones" value={fmt(k.unique_intents)} icon={BarChart3} color="#338FD9" />
          </div>
          <div className="card p-1">
            <KpiCard label="Total Fallbacks" value={fmt(k.total_fallbacks)} icon={AlertTriangle} color="#003D73" />
          </div>
          <div className="card p-1">
            <KpiCard label="Tasa Fallback" value={fmtPct(k.fallback_rate)} icon={Target} color="#5AADE0" />
          </div>
        </div>

        {/* Fallback Trend — main chart */}
        <Widget
          title="Tendencia Fallbacks"
          className="min-h-[360px]"
          onOpenQuery={() => openQuery('Tendencia Fallbacks', botTab.data.fallbackTrend, 'combo')}
          onExport={() => botTab.data?.fallbackTrend && exportCsv(botTab.data.fallbackTrend.data, botTab.data.fallbackTrend.columns, 'fallback_trend')}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Barras = Cantidad de fallbacks &middot; Linea = Tasa de fallback %
            </p>
            <PeriodSelector value={fallbackPeriod} onChange={v => setFallbackPeriod(v)} />
          </div>
          <FallbackTrendChart data={botTab.data.fallbackTrend?.data || []} />
        </Widget>

        {/* Fallbacks por Intent + Top Intenciones */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget
            title="Fallbacks por Intent"
            className="min-h-[300px]"
            onOpenQuery={() => openQuery('Fallbacks por Intent', botTab.data.fallbackIntent, 'bar_horizontal')}
            onExport={() => botTab.data?.fallbackIntent && exportCsv(botTab.data.fallbackIntent.data, botTab.data.fallbackIntent.columns, 'fallback_por_intent')}
          >
            {renderChart(botTab.data.fallbackIntent, 'bar_horizontal', 260)}
          </Widget>
          <Widget
            title="Top Intenciones Bot"
            className="min-h-[300px]"
            onOpenQuery={() => openQuery('Top Intenciones Bot', botTab.data.topIntents, 'bar_horizontal')}
          >
            {renderChart(botTab.data.topIntents, 'bar_horizontal', 260)}
          </Widget>
        </div>

        {/* Fallback Intent Table */}
        <Widget
          title="Detalle Fallbacks por Intent"
          className="min-h-[200px]"
          onExport={() => botTab.data?.fallbackIntent && exportCsv(botTab.data.fallbackIntent.data, botTab.data.fallbackIntent.columns, 'fallback_detail')}
          onOpenQuery={() => openQuery('Fallbacks por Intent', botTab.data.fallbackIntent, 'table')}
        >
          <SimpleTable {...(botTab.data.fallbackIntent || emptyDf)} />
        </Widget>
      </div>
    )
  }

  // ─── Main render ───────────────────────────────────────────

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    general: renderGeneral,
    bot: renderBot,
  }

  return (
    <div className="animate-fade-in -mx-6 -my-6">
      <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
        {/* Header */}
        <div className="px-6 py-4" style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
          <div className="max-w-[1400px] mx-auto flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>WhatsApp Analytics — NPS & Bot</h1>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Satisfaccion del cliente + Rendimiento del bot — Encuestas NPS y Fallbacks</p>
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
                onClick={handleEditDashboard}
                className="flex items-center gap-1 text-xs px-3 py-1.5 font-medium rounded-btn transition-colors"
                style={{ border: '1px solid var(--border)', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-card)' }}
                title="Clonar y editar en el constructor de dashboards"
              >
                <Pencil size={12} />
                Editar
              </button>
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
    const tabData = activeTab === 'general' ? general : botTab
    if (!tabData?.data?.kpis) return kpis
    for (const [key, val] of Object.entries(tabData.data.kpis)) {
      if (val !== null && val !== undefined) kpis[key] = val as string | number
    }
    return kpis
  }
}
