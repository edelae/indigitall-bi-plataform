import { useEffect, useState, useCallback } from 'react'
import {
  MessageSquare, Bot, Headphones, Send, Shield,
  RefreshCw, Download, Calendar, Loader2,
  Users, Clock, PhoneCall, BarChart3, Zap, AlertTriangle,
  TrendingUp, Hash, Target,
} from 'lucide-react'
import KpiCard from '../components/KpiCard'
import ChartWidget from '../components/ChartWidget'
import { fetchAnalytics } from '../api/client'
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

function Widget({ title, children, className = '', onExport }: {
  title: string; children: React.ReactNode; className?: string;
  onExport?: () => void
}) {
  return (
    <div className={`bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-4 flex flex-col ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#374151]">{title}</h3>
        {onExport && (
          <button
            onClick={onExport}
            className="text-[#9CA3AF] hover:text-[#0066CC] transition-colors p-1"
            title="Descargar CSV"
          >
            <Download size={14} />
          </button>
        )}
      </div>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  )
}

// ─── Data Table ──────────────────────────────────────────────────

function SimpleTable({ data, columns }: DfResponse) {
  if (!data.length) return <p className="text-sm text-[#9CA3AF] text-center py-4">Sin datos</p>
  return (
    <div className="overflow-auto max-h-[400px]">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-[#F9FAFB]">
          <tr>
            {columns.map(c => (
              <th key={c} className="text-left px-2 py-1.5 font-medium text-[#6B7280] border-b border-[#E5E7EB]">
                {c.replace(/_/g, ' ').replace(/\b\w/g, x => x.toUpperCase())}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-[#F3F4F6] hover:bg-[#F9FAFB]">
              {columns.map(c => (
                <td key={c} className="px-2 py-1.5 text-[#374151]">
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
    ]).then(([kpis, agents, reasons, trend, frt, handle, queue, convTypeTrend]) => {
      setCc({ data: { kpis, agents, reasons, trend, frt, handle, queue, convTypeTrend }, loading: false, error: null, fetched: true })
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

  function renderChart(df: DfResponse | undefined, type: ChartType, height = 280) {
    if (!df || !df.data?.length) return <p className="text-sm text-[#9CA3AF] text-center py-8">Sin datos</p>
    return <ChartWidget data={df.data} columns={df.columns} chartType={type} height={height} fillContainer />
  }

  // ─── WhatsApp Tab ────────────────────────────────────────────

  function renderWhatsApp() {
    if (!wa.data) return null
    const k = wa.data.kpis
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Total Mensajes" value={fmt(k.total_messages)} icon={MessageSquare} color="#0066CC" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Contactos Unicos" value={fmt(k.unique_contacts)} icon={Users} color="#00A86B" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Tasa Fallback" value={fmtPct(k.fallback_rate)} icon={AlertTriangle} color="#EF4444" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Tasa Entrega" value={fmtPct(k.delivery_rate)} icon={Target} color="#0099FF" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <Widget title="Mensajes por Hora" className="lg:col-span-3 min-h-[300px]">
            {renderChart(wa.data.byHour, 'bar', 260)}
          </Widget>
          <Widget title="Distribucion Bot / Humano" className="lg:col-span-2 min-h-[300px]">
            {renderChart(wa.data.botHuman, 'pie', 260)}
          </Widget>
        </div>
        <Widget title="Tendencia Diaria de Mensajes" className="min-h-[320px]">
          {renderChart(wa.data.trend, 'area', 280)}
        </Widget>
        <Widget title="Heatmap — Mensajes por Hora y Dia" className="min-h-[300px]">
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
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Total Mensajes" value={fmt(k.total_messages)} icon={MessageSquare} color="#0066CC" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Contactos" value={fmt(k.unique_contacts)} icon={Users} color="#00A86B" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Tasa Fallback" value={fmtPct(k.fallback_rate)} icon={AlertTriangle} color="#EF4444" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Resolucion Bot" value={fmtPct(k.bot_resolution_pct)} icon={Bot} color="#0099FF" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Espera Promedio" value={fmtTime(k.avg_wait_seconds)} icon={Clock} color="#F59E0B" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Tendencia Tasa Fallback" className="min-h-[300px]">
            {renderChart(bot.data.fallback, 'line', 260)}
          </Widget>
          <Widget title="Top Intenciones" className="min-h-[300px]">
            {renderChart(bot.data.intents, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Distribucion Bot / Humano" className="min-h-[300px]">
            {renderChart(bot.data.botHuman, 'pie', 260)}
          </Widget>
          <Widget title="Tipos de Contenido" className="min-h-[300px]">
            {renderChart(bot.data.content, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <Widget title="Heatmap — Mensajes por Hora y Dia" className="min-h-[300px]">
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
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Conversaciones" value={fmt(k.total_conversations)} icon={PhoneCall} color="#0066CC" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Agentes Activos" value={fmt(k.active_agents)} icon={Users} color="#00A86B" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="FRT Promedio" value={fmtTime(k.avg_frt_seconds)} icon={Zap} color="#F59E0B" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Handle Time" value={fmtTime(k.avg_handle_seconds)} icon={Clock} color="#0099FF" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="FCR" value={fmtPct(k.fcr_rate)} icon={Target} color="#00A86B" />
          </div>
        </div>
        <Widget
          title="Rendimiento de Agentes"
          className="min-h-[200px]"
          onExport={() => cc.data?.agents && exportCsv(cc.data.agents.data, cc.data.agents.columns, 'agentes')}
        >
          <SimpleTable {...(cc.data.agents || emptyDf)} />
        </Widget>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Razones de Cierre" className="min-h-[300px]">
            {renderChart(cc.data.reasons, 'pie', 260)}
          </Widget>
          <Widget title="Conversaciones en el Tiempo" className="min-h-[300px]">
            {renderChart(cc.data.trend, 'area', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Tendencia FRT" className="min-h-[300px]">
            {renderChart(cc.data.frt, 'line', 260)}
          </Widget>
          <Widget title="Tendencia Handle Time" className="min-h-[300px]">
            {renderChart(cc.data.handle, 'line', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Cola por Hora" className="min-h-[300px]">
            {renderChart(cc.data.queue, 'bar', 260)}
          </Widget>
          <Widget title="Tipo Conversacion (Bot/Humano/Mixta)" className="min-h-[300px]">
            {renderChart(cc.data.convTypeTrend, 'area_stacked', 260)}
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
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Enviados" value={fmt(k.total_enviados)} icon={Send} color="#0066CC" />
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Total Chunks" value={fmt(k.total_chunks)} icon={Hash} color="#00A86B" />
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Entregados" value={fmt(k.total_delivered)} icon={BarChart3} color="#76C043" />
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Clicks" value={fmt(k.total_clicks)} icon={Target} color="#F59E0B" />
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Campanas" value={fmt(k.campanas)} icon={BarChart3} color="#0099FF" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Enviados vs Chunks" className="min-h-[300px]">
            {renderChart(sms.data.trend, 'line', 260)}
          </Widget>
          <Widget title="Tipo de Envio" className="min-h-[300px]">
            {renderChart(sms.data.types, 'pie', 260)}
          </Widget>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Top Campanas por Volumen" className="min-h-[300px]">
            {renderChart(sms.data.campaigns, 'bar_horizontal', 260)}
          </Widget>
          <Widget title="Top Campanas por Chunks/Envio" className="min-h-[300px]">
            {renderChart(sms.data.campaignsCtr, 'bar_horizontal', 260)}
          </Widget>
        </div>
        <Widget title="Heatmap — SMS por Hora y Dia" className="min-h-[300px]">
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
        <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-4">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-[#374151]">
              Umbral de sobre-toque:
            </label>
            <input
              type="range" min={1} max={10} value={threshold}
              onChange={e => { setThreshold(Number(e.target.value)); setToques(s => ({ ...s, fetched: false })) }}
              className="flex-1 max-w-[200px] accent-[#0066CC]"
            />
            <span className="text-sm font-bold text-[#0066CC] w-6">{threshold}</span>
            <span className="text-xs text-[#9CA3AF]">mensajes/contacto/semana</span>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="% Sobre-tocados" value={fmtPct(k.pct_over_touched)} icon={AlertTriangle} color="#EF4444" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Contacto-Semanas" value={fmt(k.total_contact_weeks)} icon={Users} color="#0066CC" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Sobre-tocados" value={fmt(k.over_touched)} icon={Shield} color="#F59E0B" />
          </div>
          <div className="bg-white rounded-lg shadow-[0_1px_4px_rgba(0,0,0,0.08)] p-1">
            <KpiCard label="Prom. Msgs/Contacto" value={fmt(k.avg_msgs_per_contact_week, 1)} icon={TrendingUp} color="#00A86B" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Widget title="Distribucion de Toques por Contacto" className="min-h-[300px]">
            {renderChart(toques.data.dist, 'bar', 260)}
          </Widget>
          <Widget title="Tendencia Semanal % Sobre-tocados" className="min-h-[300px]">
            {renderChart(toques.data.weeklyTrend, 'line', 260)}
          </Widget>
        </div>

        <Widget
          title="Contactos Sobre-tocados"
          className="min-h-[200px]"
          onExport={() => toques.data?.overTouched && exportCsv(toques.data.overTouched.data, toques.data.overTouched.columns, 'sobre_tocados')}
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
      <div className="min-h-screen bg-[#F3F4F6]">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-6 py-4">
          <div className="max-w-[1400px] mx-auto flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-xl font-bold text-[#111827]">Dashboard Visionamos</h1>
              <p className="text-xs text-[#9CA3AF]">WhatsApp + Contact Center + SMS — Datos en tiempo real</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Calendar size={14} className="text-[#9CA3AF]" />
                <input
                  type="date" value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="text-xs border border-[#D1D5DB] rounded px-2 py-1 text-[#374151]"
                />
                <span className="text-xs text-[#9CA3AF]">—</span>
                <input
                  type="date" value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="text-xs border border-[#D1D5DB] rounded px-2 py-1 text-[#374151]"
                />
              </div>
              <button
                onClick={() => setRefreshKey(k => k + 1)}
                className="flex items-center gap-1 text-xs bg-[#0066CC] text-white px-3 py-1.5 rounded hover:bg-[#005299] transition-colors"
              >
                <RefreshCw size={12} />
                Actualizar
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white border-b border-[#E5E7EB]">
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
                      ? 'border-[#0066CC] text-[#0066CC]'
                      : 'border-transparent text-[#6B7280] hover:text-[#374151] hover:border-[#D1D5DB]'
                  }`}
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
    </div>
  )
}
