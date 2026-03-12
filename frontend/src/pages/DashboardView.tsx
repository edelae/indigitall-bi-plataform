import { useEffect, useState, useRef, useMemo, Component, type ReactNode } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Pencil, Loader2, ArrowLeft, Info, X, ExternalLink, AlertTriangle } from 'lucide-react'
import { Responsive } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import KpiCard from '../components/KpiCard'
import DashboardAnalyst from '../components/DashboardAnalyst'
import type { Dashboard, DashboardWidget, ChartType } from '../types'
import { PRIMARY_COLOR, COLOR_PALETTES } from '../types'
import { getDashboard } from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

// Grid constants — IDENTICAL to DashboardBuilder
const GRID_COLS = { lg: 12, md: 10, sm: 6, xs: 4 }
const GRID_BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480 }
const GRID_ROW_HEIGHT = 80
const GRID_MARGIN: [number, number] = [8, 8]
const GRID_PADDING: [number, number] = [8, 8]

// Hook: measure container width (ResizeObserver + rAF fallback + window fallback)
function useContainerWidth(ref: React.RefObject<HTMLDivElement | null>): number {
  const [width, setWidth] = useState(() => {
    // Initial fallback: use window width minus sidebar/padding
    return typeof window !== 'undefined' ? Math.max(window.innerWidth - 120, 400) : 1000
  })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = (w: number) => { if (w > 0) setWidth(w) }
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) update(entry.contentRect.width)
    })
    ro.observe(el)
    update(el.getBoundingClientRect().width)
    // Fallback: re-measure after layout paint
    requestAnimationFrame(() => update(el.getBoundingClientRect().width))
    // Double fallback: another rAF after one frame
    requestAnimationFrame(() => requestAnimationFrame(() => update(el.getBoundingClientRect().width)))
    return () => ro.disconnect()
  }, [ref])
  return width
}

const TEXT_SIZE_CLASS: Record<string, string> = {
  xs: 'text-xs', sm: 'text-sm', base: 'text-base',
  lg: 'text-lg', xl: 'text-xl', '2xl': 'text-2xl',
}

interface DashboardTab {
  id: string
  name: string
  widgets: DashboardWidget[]
}

// Error boundary to catch runtime render errors
class WidgetErrorBoundary extends Component<
  { children: ReactNode; widgetTitle?: string },
  { hasError: boolean; error?: Error }
> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-4 text-center">
          <AlertTriangle size={20} className="text-amber-500 mb-2" />
          <p className="text-xs text-[#6B7280]">Error al renderizar</p>
          <p className="text-[10px] text-[#9CA3AF] mt-1">{this.props.widgetTitle}</p>
        </div>
      )
    }
    return this.props.children
  }
}

export default function DashboardView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [infoModal, setInfoModal] = useState<DashboardWidget | null>(null)
  const [tabs, setTabs] = useState<DashboardTab[]>([])
  const [activeTabId, setActiveTabId] = useState('')
  const [ready, setReady] = useState(false)
  const canvasRef = useRef<HTMLDivElement>(null)
  const canvasWidth = useContainerWidth(canvasRef)

  // Defer heavy grid render until after first paint
  useEffect(() => {
    const raf = requestAnimationFrame(() => setReady(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    getDashboard(parseInt(id))
      .then(d => {
        setDashboard(d)
        const layout = d.layout || []
        if (layout.length > 0 && layout[0]?.tab_id) {
          const tabMap = new Map<string, DashboardTab>()
          for (const w of layout) {
            const tid = w.tab_id || 'tab-1'
            const tname = w.tab_name || 'General'
            if (!tabMap.has(tid)) tabMap.set(tid, { id: tid, name: tname, widgets: [] })
            tabMap.get(tid)!.widgets.push({
              ...w,
              grid_i: w.grid_i || `w-${tabMap.get(tid)!.widgets.length}`,
              grid_x: w.grid_x ?? 0,
              grid_y: w.grid_y ?? 0,
              grid_w: w.grid_w ?? w.width ?? 6,
              grid_h: w.grid_h ?? 4,
            })
          }
          const loadedTabs = Array.from(tabMap.values())
          setTabs(loadedTabs)
          setActiveTabId(loadedTabs[0].id)
        } else {
          const widgets = layout.map((w: any, i: number) => ({
            ...w,
            grid_i: w.grid_i || `widget-${i}`,
            grid_x: w.grid_x ?? (i % 2) * 6,
            grid_y: w.grid_y ?? Math.floor(i / 2) * 4,
            grid_w: w.grid_w ?? w.width ?? 6,
            grid_h: w.grid_h ?? 4,
          }))
          setTabs([{ id: 'tab-1', name: 'General', widgets }])
          setActiveTabId('tab-1')
        }
      })
      .catch(err => {
        console.error('Dashboard load error:', err)
        setError(err?.message || 'Error al cargar el tablero')
        setDashboard(null)
      })
      .finally(() => setLoading(false))
  }, [id])

  // Collect real KPI / widget data for DashboardAnalyst context
  const analystKpis = useMemo(() => {
    const kpis: Record<string, string | number> = {}
    const allWidgets = tabs.flatMap(t => t.widgets)
    for (const w of allWidgets) {
      const label = w.custom_title || w.title
      if ((w.type === 'kpi' || w.chart_type === 'kpi') && w.kpi_value !== undefined) {
        kpis[label] = w.kpi_value
      } else if (w.data && w.data.length > 0 && w.columns && w.columns.length >= 1) {
        if (w.data.length === 1) {
          for (const col of w.columns) {
            kpis[`${label} — ${col}`] = w.data[0][col]
          }
        } else {
          kpis[`${label} (filas)`] = w.data.length
          if (w.columns.length >= 2) {
            const xCol = w.columns[0]
            const yCol = w.columns[1]
            const top5 = w.data.slice(0, 5).map(r => `${r[xCol]}: ${r[yCol]}`).join(', ')
            kpis[`${label} — top datos`] = top5
          }
        }
      }
    }
    return kpis
  }, [tabs])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div className="text-center py-24">
        <AlertTriangle size={40} className="text-amber-500 mx-auto mb-3" />
        <p className="text-[#374151] font-medium mb-1">No se pudo cargar el tablero</p>
        <p className="text-sm text-[#6B7280] mb-4">{error || 'Tablero no encontrado'}</p>
        <Link to="/tableros" className="btn-primary text-sm no-underline">Volver a tableros</Link>
      </div>
    )
  }

  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0]
  const widgets = activeTab?.widgets || []

  // Build react-grid-layout compatible layout
  const gridLayout = widgets.map(w => ({
    i: w.grid_i,
    x: w.grid_x ?? 0,
    y: w.grid_y ?? 0,
    w: w.grid_w ?? 6,
    h: w.grid_h ?? 4,
  }))

  const handleChartClick = (widget: DashboardWidget) => {
    if (widget.query_id) {
      navigate(`/consultas/nueva?rerun=${widget.query_id}`)
    } else if (widget.query_text) {
      navigate(`/consultas/nueva?q=${encodeURIComponent(widget.query_text)}`)
    } else if (widget.sql) {
      navigate(`/consultas/nueva?q=${encodeURIComponent(widget.sql)}`)
    }
  }

  const isClickable = (widget: DashboardWidget) => {
    return !!(widget.query_id || widget.query_text || widget.sql)
  }

  // Determine if a widget should render as KPI
  const isKpiWidget = (w: DashboardWidget) => {
    if ((w.type === 'kpi' || w.chart_type === 'kpi') && w.kpi_value !== undefined) return true
    // Auto-detect: single-row result with 1 column and no chart_type
    if (w.data?.length === 1 && w.columns?.length === 1 && !w.chart_type) return true
    return false
  }

  const getKpiValue = (w: DashboardWidget) => {
    if (w.kpi_value !== undefined) return w.kpi_value
    if (w.data?.length === 1 && w.columns?.length >= 1) {
      return w.data[0][w.columns[w.columns.length > 1 ? 1 : 0]]
    }
    return '—'
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-[#111827] tracking-tight">{dashboard.name}</h1>
          {dashboard.description && (
            <p className="text-sm text-[#6B7280] mt-0.5 max-w-xl">{dashboard.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link
            to={`/tableros/nuevo?edit=${dashboard.id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#374151] bg-white border border-[#D1D5DB] rounded-lg hover:bg-[#F9FAFB] transition-colors no-underline"
          >
            <Pencil size={14} /> Editar
          </Link>
          <Link
            to="/tableros"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#6B7280] hover:text-[#374151] transition-colors no-underline"
          >
            <ArrowLeft size={14} /> Tableros
          </Link>
        </div>
      </div>

      {/* Tabs */}
      {tabs.length > 1 && (
        <div className="flex items-center gap-1 mb-0 bg-white border border-[#E5E7EB] rounded-t-xl px-3 py-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeTabId === tab.id
                  ? 'bg-[#1E88E5] text-white shadow-sm'
                  : 'text-[#6B7280] hover:text-[#374151] hover:bg-[#F3F4F6]'
              }`}
            >
              {tab.name}
            </button>
          ))}
        </div>
      )}

      {/* Canvas — react-grid-layout Responsive (read-only, matches builder) */}
      <div
        ref={canvasRef}
        className={`bg-[#F8F9FB] min-h-[400px] ${tabs.length > 1 ? 'rounded-b-xl' : 'rounded-xl'} border border-[#E5E7EB] ${tabs.length > 1 ? 'border-t-0' : ''}`}
      >
        {widgets.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-[#6B7280] mb-4">Este tablero no tiene widgets</p>
            <Link
              to={`/tableros/nuevo?edit=${dashboard.id}`}
              className="btn-primary text-sm no-underline inline-flex items-center gap-1.5"
            >
              <Pencil size={14} /> Editar tablero
            </Link>
          </div>
        ) : !ready ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-primary" />
            <span className="ml-2 text-sm text-[#6B7280]">Cargando widgets...</span>
          </div>
        ) : (
          <Responsive
            width={canvasWidth}
            layouts={{ lg: gridLayout, md: gridLayout, sm: gridLayout, xs: gridLayout }}
            breakpoints={GRID_BREAKPOINTS}
            cols={GRID_COLS}
            rowHeight={GRID_ROW_HEIGHT}
            isDraggable={false}
            isResizable={false}
            compactType="vertical"
            margin={GRID_MARGIN}
            containerPadding={GRID_PADDING}
            style={{ minHeight: 400 }}
          >
            {widgets.map(w => (
              <div key={w.grid_i}>
                <WidgetErrorBoundary widgetTitle={w.title}>
                  <div
                    className="bg-white h-full flex flex-col overflow-hidden border border-[#E8EAF0]"
                    style={{
                      borderRadius: 12,
                      boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)',
                    }}
                  >
                    {/* Title block */}
                    {w.is_title_block ? (
                      <div className="flex items-center justify-center h-full px-4">
                        <h2
                          className={`${TEXT_SIZE_CLASS[w.text_size || 'lg']} font-bold text-[#111827] text-center`}
                          style={{ fontFamily: w.font_family || 'Inter' }}
                        >
                          {w.text_content || w.title}
                        </h2>
                      </div>
                    ) : w.type === 'text_card' ? (
                      <div className="flex flex-col h-full p-4">
                        <p className={`${TEXT_SIZE_CLASS[w.text_size || 'sm']} text-[#374151] flex-1`}>
                          {w.text_content}
                        </p>
                        {w.text_url && (
                          <a
                            href={w.text_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary mt-2 underline"
                          >
                            {w.text_url}
                          </a>
                        )}
                      </div>
                    ) : (
                      <>
                        {/* Widget header */}
                        <div className="flex items-center justify-between px-3 py-2 border-b border-[#F0F1F5] flex-shrink-0">
                          <span
                            className="font-semibold text-[#111827] truncate"
                            style={{
                              fontSize: w.title_font_size || 13,
                              fontFamily: w.font_family || 'Inter',
                            }}
                          >
                            {w.custom_title || w.title}
                          </span>
                          <button
                            onClick={() => setInfoModal(w)}
                            className="p-1 hover:bg-[#F3F4F6] rounded-md transition-colors"
                            title="Ver info"
                          >
                            <Info size={12} className="text-[#9CA3AF]" />
                          </button>
                        </div>

                        {/* Widget content */}
                        <div
                          className={`flex-1 overflow-hidden flex flex-col ${isClickable(w) ? 'cursor-pointer hover:bg-[#FAFBFC] transition-colors' : ''}`}
                          onClick={() => isClickable(w) && handleChartClick(w)}
                          title={isClickable(w) ? 'Clic para ir a la consulta' : undefined}
                          style={{ minHeight: 0 }}
                        >
                          {isKpiWidget(w) ? (
                            <div className="flex-1 flex items-center justify-center">
                              <KpiCard
                                label={w.kpi_label || w.title}
                                value={getKpiValue(w)}
                                color={w.kpi_color || PRIMARY_COLOR}
                                delta={w.kpi_delta}
                                kpiStyle={w.kpi_style || 'accent'}
                                maxValue={w.kpi_max_value}
                              />
                            </div>
                          ) : w.data && w.data.length > 0 && w.columns && w.columns.length >= 2 ? (
                            <div className="flex-1" style={{ position: 'relative', minHeight: 0 }}>
                              <div style={{ position: 'absolute', inset: 4 }}>
                                <ChartWidget
                                  data={w.data.length > 500 ? w.data.slice(0, 500) : w.data}
                                  columns={w.columns}
                                  chartType={(w.chart_type || w.type || 'bar') as ChartType}
                                  fillContainer
                                  colors={
                                    w.color_palette
                                      ? COLOR_PALETTES[w.color_palette]?.colors
                                      : undefined
                                  }
                                  xLabel={w.custom_x_label}
                                  yLabel={w.custom_y_label}
                                  showLegend={w.show_legend !== false}
                                  fontFamily={w.font_family}
                                  axisFontSize={w.axis_font_size}
                                  legendFontSize={w.legend_font_size}
                                  xColumn={w.x_column}
                                  yColumns={w.y_columns}
                                  groupByColumn={w.group_by_column}
                                />
                              </div>
                            </div>
                          ) : w.data && w.data.length > 0 ? (
                            <div className="flex-1 text-xs overflow-auto p-2">
                              <table className="w-full">
                                <thead>
                                  <tr className="bg-[#F9FAFB]">
                                    {w.columns.map(c => (
                                      <th
                                        key={c}
                                        className="px-2 py-1 text-left text-[10px] font-semibold text-[#6B7280]"
                                      >
                                        {c}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {w.data.slice(0, 10).map((row, ri) => (
                                    <tr key={ri} className="border-b border-[#F3F4F6]">
                                      {w.columns.map(c => (
                                        <td
                                          key={c}
                                          className="px-2 py-1 text-[10px] truncate max-w-[150px]"
                                        >
                                          {String(row[c] ?? '')}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="flex-1 flex items-center justify-center text-xs text-[#9CA3AF]">
                              Sin datos
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </WidgetErrorBoundary>
              </div>
            ))}
          </Responsive>
        )}
      </div>

      {/* AI Analyst Panel — with real dashboard data */}
      <DashboardAnalyst
        context={{
          activeTab: activeTabId,
          kpis: analystKpis,
        }}
      />

      {/* Info Modal */}
      {infoModal && (
        <div
          className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]"
          onClick={() => setInfoModal(null)}
        >
          <div
            className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
            style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
              <h3 className="font-semibold text-[#111827]">
                {infoModal.custom_title || infoModal.title}
              </h3>
              <button
                onClick={() => setInfoModal(null)}
                className="p-1 hover:bg-[#F3F4F6] rounded-md transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-4 space-y-3">
              {infoModal.query_text && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">Pregunta original</p>
                  <p className="text-sm text-[#374151]">{infoModal.query_text}</p>
                </div>
              )}
              <div className="flex gap-2">
                <span className="text-[9px] px-1.5 py-0.5 bg-[#1E88E5]/10 text-[#1E88E5] rounded font-medium">
                  {(infoModal.chart_type || infoModal.type || 'table').toUpperCase()}
                </span>
                <span className="text-[9px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded font-medium">
                  {infoModal.data?.length || 0} filas
                </span>
              </div>
              {infoModal.sql && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">SQL</p>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-lg text-xs overflow-x-auto font-mono whitespace-pre-wrap">
                    {infoModal.sql}
                  </pre>
                </div>
              )}
              {(infoModal.query_id || infoModal.query_text || infoModal.sql) && (
                <Link
                  to={
                    infoModal.query_id
                      ? `/consultas/nueva?rerun=${infoModal.query_id}`
                      : `/consultas/nueva?q=${encodeURIComponent(infoModal.query_text || infoModal.sql || '')}`
                  }
                  className="btn-primary text-sm inline-flex items-center gap-1.5 no-underline"
                >
                  <ExternalLink size={14} /> Ir a la consulta
                </Link>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
