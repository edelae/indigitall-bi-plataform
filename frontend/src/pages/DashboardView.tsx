import { useEffect, useState, useMemo, useCallback, Component, type ReactNode } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Pencil, Loader2, ArrowLeft, Info, X, ExternalLink, AlertTriangle, Calendar, Filter, ChevronDown } from 'lucide-react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import KpiCard from '../components/KpiCard'
import DashboardAnalyst from '../components/DashboardAnalyst'
import type { Dashboard, DashboardWidget, ChartType, DashboardGranularity, DashboardFilter } from '../types'
import { PRIMARY_COLOR, COLOR_PALETTES, GRANULARITY_OPTIONS, transformSqlGranularity, getCardStyle, detectFilterableColumns, applyDashboardFilters } from '../types'
import { getDashboard, executeSql } from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGrid = WidthProvider(Responsive)

// Grid constants — IDENTICAL to DashboardBuilder
const GRID_COLS = { lg: 12, md: 12, sm: 6, xs: 4 }
const GRID_BREAKPOINTS = { lg: 1200, md: 900, sm: 600, xs: 0 }
const GRID_ROW_HEIGHT = 80
const GRID_MARGIN: [number, number] = [8, 8]
const GRID_PADDING: [number, number] = [8, 8]

const TEXT_SIZE_CLASS: Record<string, string> = {
  xs: 'text-xs', sm: 'text-sm', base: 'text-base',
  lg: 'text-lg', xl: 'text-xl', '2xl': 'text-2xl',
}

interface DashboardTab {
  id: string
  name: string
  widgets: DashboardWidget[]
}

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
  const [granularity, setGranularity] = useState<DashboardGranularity>('original')
  const [granLoading, setGranLoading] = useState(false)
  const [dashFilters, setDashFilters] = useState<DashboardFilter[]>([])
  const [filterPanelOpen, setFilterPanelOpen] = useState(false)
  const [filterLoading, setFilterLoading] = useState(false)

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
              original_sql: w.sql || w.original_sql,
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
            original_sql: w.sql || w.original_sql,
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

  // Granularity filter — re-execute all widgets with transformed SQL
  const handleGranularityChange = useCallback(async (gran: DashboardGranularity) => {
    setGranularity(gran)
    setGranLoading(true)
    setTabs(prev => prev.map(tab => ({
      ...tab,
      widgets: tab.widgets.map(w => {
        const origSql = w.original_sql || w.sql
        if (!origSql || !origSql.match(/DATE_TRUNC/i)) return w
        return { ...w, _pending: true } as any
      }),
    })))

    // Process all tabs
    const newTabs = await Promise.all(tabs.map(async tab => {
      const newWidgets = await Promise.all(tab.widgets.map(async w => {
        const origSql = w.original_sql || w.sql
        if (!origSql || !origSql.match(/DATE_TRUNC/i)) return w
        const transformed = transformSqlGranularity(origSql, gran)
        try {
          const res = await executeSql(transformed)
          return { ...w, data: res.data, columns: res.columns, sql: transformed }
        } catch {
          return w
        }
      }))
      return { ...tab, widgets: newWidgets }
    }))
    setTabs(newTabs)
    setGranLoading(false)
  }, [tabs])

  // Check if any widget has DATE_TRUNC
  const hasDateTruncWidgets = useMemo(() => {
    return tabs.some(t => t.widgets.some(w => (w.original_sql || w.sql || '').match(/DATE_TRUNC/i)))
  }, [tabs])

  // Dashboard-level variable filters
  const availableFilterColumns = useMemo(() => {
    const allWidgets = tabs.flatMap(t => t.widgets)
    return detectFilterableColumns(allWidgets)
  }, [tabs])

  const addDashFilter = (col: string) => {
    if (dashFilters.some(f => f.column === col)) return
    const colInfo = availableFilterColumns.find(c => c.column === col)
    if (!colInfo) return
    setDashFilters(prev => [...prev, {
      id: `filter-${Date.now()}`, column: col,
      label: col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      values: colInfo.values, selected: [],
    }])
  }

  const toggleFilterValue = (filterId: string, value: string) => {
    setDashFilters(prev => prev.map(f => {
      if (f.id !== filterId) return f
      const sel = f.selected.includes(value)
        ? f.selected.filter(v => v !== value)
        : [...f.selected, value]
      return { ...f, selected: sel }
    }))
  }

  const applyFilters = useCallback(async () => {
    const activeFilters = dashFilters.filter(f => f.selected.length > 0 && f.selected.length < f.values.length)
    if (!activeFilters.length) {
      setTabs(prev => prev.map(tab => ({
        ...tab, widgets: tab.widgets.map(w => w.original_sql ? { ...w, sql: w.original_sql } : w),
      })))
      return
    }
    setFilterLoading(true)
    const newTabs = await Promise.all(tabs.map(async tab => {
      const newWidgets = await Promise.all(tab.widgets.map(async w => {
        const origSql = w.original_sql || w.sql
        if (!origSql) return w
        const filtered = applyDashboardFilters(origSql, activeFilters)
        if (filtered === origSql) return w
        try {
          const res = await executeSql(filtered)
          return { ...w, data: res.data, columns: res.columns, sql: filtered, original_sql: origSql }
        } catch { return w }
      }))
      return { ...tab, widgets: newWidgets }
    }))
    setTabs(newTabs)
    setFilterLoading(false)
  }, [tabs, dashFilters])

  const analystKpis = useMemo(() => {
    const kpis: Record<string, string | number> = {}
    const allWidgets = tabs.flatMap(t => t.widgets)
    for (const w of allWidgets) {
      const label = w.custom_title || w.title
      if ((w.type === 'kpi' || w.chart_type === 'kpi') && w.kpi_value !== undefined) {
        kpis[label] = w.kpi_value
      } else if (w.data && w.data.length > 0 && w.columns && w.columns.length >= 1) {
        if (w.data.length === 1) {
          for (const col of w.columns) kpis[`${label} — ${col}`] = w.data[0][col]
        } else {
          kpis[`${label} (filas)`] = w.data.length
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

  const gridLayout = widgets.map(w => ({
    i: w.grid_i,
    x: w.grid_x ?? 0,
    y: w.grid_y ?? 0,
    w: w.grid_w ?? 6,
    h: w.grid_h ?? 4,
  }))

  const handleChartClick = (widget: DashboardWidget) => {
    if (widget.query_id) navigate(`/consultas/nueva?rerun=${widget.query_id}`)
    else if (widget.query_text) navigate(`/consultas/nueva?q=${encodeURIComponent(widget.query_text)}`)
    else if (widget.sql) navigate(`/consultas/nueva?q=${encodeURIComponent(widget.sql)}`)
  }

  const isClickable = (widget: DashboardWidget) => !!(widget.query_id || widget.query_text || widget.sql)

  const isKpiWidget = (w: DashboardWidget) => {
    if ((w.type === 'kpi' || w.chart_type === 'kpi') && w.kpi_value !== undefined) return true
    if (w.data?.length === 1 && w.columns?.length === 1 && !w.chart_type) return true
    return false
  }

  const getKpiValue = (w: DashboardWidget) => {
    if (w.kpi_value !== undefined) return w.kpi_value
    if (w.data?.length === 1 && w.columns?.length >= 1) return w.data[0][w.columns[w.columns.length > 1 ? 1 : 0]]
    return '—'
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-[#111827] tracking-tight">{dashboard.name}</h1>
          {dashboard.description && (
            <p className="text-sm text-[#6B7280] mt-0.5 max-w-xl">{dashboard.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link to={`/tableros/nuevo?edit=${dashboard.id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#374151] bg-white border border-[#D1D5DB] rounded-lg hover:bg-[#F9FAFB] transition-colors no-underline">
            <Pencil size={14} /> Editar
          </Link>
          <Link to="/tableros"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[#6B7280] hover:text-[#374151] transition-colors no-underline">
            <ArrowLeft size={14} /> Tableros
          </Link>
        </div>
      </div>

      {/* Granularity filter bar */}
      {hasDateTruncWidgets && (
        <div className="flex items-center gap-2 mb-3 px-1">
          <Calendar size={14} className="text-[#6B7280]" />
          <span className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Agrupar por:</span>
          <div className="flex gap-1">
            {GRANULARITY_OPTIONS.map(opt => (
              <button key={opt.value}
                onClick={() => handleGranularityChange(opt.value)}
                disabled={granLoading}
                className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  granularity === opt.value
                    ? 'bg-[#1E88E5] text-white shadow-sm'
                    : 'bg-white text-[#6B7280] border border-[#E5E7EB] hover:border-[#1E88E5] hover:text-[#1E88E5]'
                }`}>
                {opt.label}
              </button>
            ))}
          </div>
          {granLoading && <Loader2 size={14} className="animate-spin text-primary" />}
        </div>
      )}

      {/* Dashboard Filters */}
      {availableFilterColumns.length > 0 && (
        <div className="mb-3">
          {/* Filter toggle + chips */}
          <div className="flex items-center gap-2 px-1 flex-wrap">
            <button onClick={() => setFilterPanelOpen(!filterPanelOpen)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border ${
                filterPanelOpen || dashFilters.length > 0
                  ? 'border-primary bg-primary/5 text-primary'
                  : 'border-[#E5E7EB] bg-white text-[#6B7280] hover:border-primary/30'
              }`}>
              <Filter size={12} />
              Filtros
              {dashFilters.length > 0 && <span className="bg-primary text-white text-[9px] px-1.5 py-0.5 rounded-full ml-1">{dashFilters.length}</span>}
            </button>
            {dashFilters.filter(f => f.selected.length > 0).map(f => (
              <span key={f.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-medium rounded-lg">
                {f.label}: {f.selected.length === 1 ? f.selected[0] : `${f.selected.length} valores`}
                <button onClick={() => { setDashFilters(prev => prev.map(df => df.id === f.id ? { ...df, selected: [] } : df)) }}
                  className="hover:bg-primary/20 rounded p-0.5"><X size={8} /></button>
              </span>
            ))}
            {filterLoading && <Loader2 size={12} className="animate-spin text-primary" />}
          </div>

          {/* Expanded filter panel */}
          {filterPanelOpen && (
            <div className="mt-2 bg-white border border-[#E5E7EB] rounded-lg p-3 shadow-sm">
              <div className="flex flex-wrap gap-1 mb-2">
                {availableFilterColumns.map(c => {
                  const added = dashFilters.some(f => f.column === c.column)
                  return (
                    <button key={c.column} disabled={added} onClick={() => addDashFilter(c.column)}
                      className={`px-2 py-0.5 rounded text-[10px] border transition-all ${
                        added ? 'border-green-200 bg-green-50 text-green-600' : 'border-[#E5E7EB] hover:border-primary text-[#6B7280] hover:text-primary'
                      }`}>
                      {added ? '✓ ' : '+ '}{c.column.replace(/_/g, ' ')}
                    </button>
                  )
                })}
              </div>
              {dashFilters.map(f => (
                <div key={f.id} className="border border-[#E5E7EB] rounded-lg p-2 mb-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-semibold text-[#374151]">{f.label}</span>
                    <div className="flex items-center gap-1">
                      {f.selected.length > 0 && (
                        <button onClick={() => setDashFilters(prev => prev.map(df => df.id === f.id ? { ...df, selected: [] } : df))}
                          className="text-[9px] text-primary hover:underline">Limpiar</button>
                      )}
                      <button onClick={() => setDashFilters(prev => prev.filter(df => df.id !== f.id))}
                        className="p-0.5 text-[#9CA3AF] hover:text-red-500"><X size={10} /></button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                    {f.values.map(val => (
                      <button key={val} onClick={() => toggleFilterValue(f.id, val)}
                        className={`px-2 py-0.5 rounded text-[10px] border transition-all ${
                          f.selected.includes(val)
                            ? 'border-primary bg-primary text-white'
                            : 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280] hover:border-primary/30'
                        }`}>{val}</button>
                    ))}
                  </div>
                </div>
              ))}
              {dashFilters.length > 0 && (
                <button onClick={applyFilters} disabled={filterLoading}
                  className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5">
                  {filterLoading ? <Loader2 size={12} className="animate-spin" /> : <Filter size={12} />}
                  Aplicar filtros
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      {tabs.length > 1 && (
        <div className="flex items-center gap-1 mb-0 bg-white border border-[#E5E7EB] rounded-t-xl px-3 py-2">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTabId(tab.id)}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                activeTabId === tab.id
                  ? 'bg-[#1E88E5] text-white shadow-sm'
                  : 'text-[#6B7280] hover:text-[#374151] hover:bg-[#F3F4F6]'
              }`}>
              {tab.name}
            </button>
          ))}
        </div>
      )}

      {/* Canvas */}
      <div className={`bg-[#F8F9FB] min-h-[400px] ${tabs.length > 1 ? 'rounded-b-xl' : 'rounded-xl'} border border-[#E5E7EB] ${tabs.length > 1 ? 'border-t-0' : ''}`}>
        {widgets.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-[#6B7280] mb-4">Este tablero no tiene widgets</p>
            <Link to={`/tableros/nuevo?edit=${dashboard.id}`}
              className="btn-primary text-sm no-underline inline-flex items-center gap-1.5">
              <Pencil size={14} /> Editar tablero
            </Link>
          </div>
        ) : (
          <ResponsiveGrid
            layouts={{ lg: gridLayout, md: gridLayout, sm: gridLayout, xs: gridLayout }}
            breakpoints={GRID_BREAKPOINTS}
            cols={GRID_COLS}
            rowHeight={GRID_ROW_HEIGHT}
            isDraggable={false}
            isResizable={false}
            compactType="vertical"
            margin={GRID_MARGIN}
            containerPadding={GRID_PADDING}
            measureBeforeMount
          >
            {widgets.map(w => {
              const cardSt = getCardStyle(w.card_style)
              const textColor = w.card_text_color || cardSt.color || '#111827'

              return (
                <div key={w.grid_i}>
                  <WidgetErrorBoundary widgetTitle={w.title}>
                    <div className="h-full flex flex-col overflow-hidden" style={cardSt}>
                      {/* Title block */}
                      {w.is_title_block ? (
                        <div className="flex items-center justify-center h-full px-4"
                          style={{ textAlign: w.text_align || 'center' }}>
                          <h2 className={`${TEXT_SIZE_CLASS[w.text_size || 'lg']} font-bold`}
                            style={{ fontFamily: w.font_family || 'Inter', color: textColor }}>
                            {w.text_content || w.title}
                          </h2>
                        </div>
                      ) : w.type === 'text_card' ? (
                        <div className="flex flex-col h-full p-4" style={{ textAlign: w.text_align || 'left' }}>
                          <p className={`${TEXT_SIZE_CLASS[w.text_size || 'sm']} flex-1`} style={{ color: textColor }}>
                            {w.text_content}
                          </p>
                          {w.text_url && (
                            <a href={w.text_url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-primary mt-2 underline">{w.text_url}</a>
                          )}
                        </div>
                      ) : (
                        <>
                          {/* Widget header */}
                          {!w.hide_header && (
                            <div className="flex items-center justify-between px-3 py-2 flex-shrink-0"
                              style={{ borderBottom: `1px solid ${textColor === '#FFFFFF' || textColor === '#F9FAFB' ? 'rgba(255,255,255,0.15)' : '#F0F1F5'}` }}>
                              <span className="font-semibold truncate"
                                style={{ fontSize: w.title_font_size || 13, fontFamily: w.font_family || 'Inter', color: textColor }}>
                                {w.custom_title || w.title}
                              </span>
                              <button onClick={() => setInfoModal(w)}
                                className="p-1 hover:bg-black/10 rounded-md transition-colors" title="Ver info">
                                <Info size={12} style={{ color: textColor === '#FFFFFF' || textColor === '#F9FAFB' ? 'rgba(255,255,255,0.5)' : '#9CA3AF' }} />
                              </button>
                            </div>
                          )}

                          {/* Widget content */}
                          <div className={`flex-1 overflow-hidden flex flex-col ${isClickable(w) ? 'cursor-pointer transition-colors' : ''}`}
                            onClick={() => isClickable(w) && handleChartClick(w)}
                            title={isClickable(w) ? 'Clic para ir a la consulta' : undefined}
                            style={{ minHeight: 0 }}>
                            {isKpiWidget(w) ? (
                              <div className="flex-1 flex items-center justify-center">
                                <KpiCard label={w.kpi_label || w.title} value={getKpiValue(w)}
                                  color={w.kpi_color || PRIMARY_COLOR} delta={w.kpi_delta}
                                  kpiStyle={w.kpi_style || 'accent'} maxValue={w.kpi_max_value} />
                              </div>
                            ) : w.data && w.data.length > 0 && w.columns && w.columns.length >= 2 ? (
                              <div className="flex-1" style={{ position: 'relative', minHeight: 0 }}>
                                <div style={{ position: 'absolute', inset: 4 }}>
                                  <ChartWidget
                                    data={w.data.length > 500 ? w.data.slice(0, 500) : w.data}
                                    columns={w.columns}
                                    chartType={(w.chart_type || w.type || 'bar') as ChartType}
                                    fillContainer
                                    colors={w.color_palette ? COLOR_PALETTES[w.color_palette]?.colors : undefined}
                                    xLabel={w.custom_x_label} yLabel={w.custom_y_label}
                                    showLegend={w.show_legend !== false}
                                    fontFamily={w.font_family} axisFontSize={w.axis_font_size}
                                    legendFontSize={w.legend_font_size}
                                    xColumn={w.x_column} yColumns={w.y_columns}
                                    groupByColumn={w.group_by_column} />
                                </div>
                              </div>
                            ) : w.data && w.data.length > 0 ? (
                              <div className="flex-1 text-xs overflow-auto p-2">
                                <table className="w-full">
                                  <thead><tr style={{ backgroundColor: textColor === '#FFFFFF' ? 'rgba(255,255,255,0.1)' : '#F9FAFB' }}>
                                    {w.columns.map(c => (
                                      <th key={c} className="px-2 py-1 text-left text-[10px] font-semibold" style={{ color: textColor }}>{c}</th>
                                    ))}
                                  </tr></thead>
                                  <tbody>
                                    {w.data.slice(0, 10).map((row, ri) => (
                                      <tr key={ri} style={{ borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                                        {w.columns.map(c => (
                                          <td key={c} className="px-2 py-1 text-[10px] truncate max-w-[150px]"
                                            style={{ color: textColor }}>{String(row[c] ?? '')}</td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <div className="flex-1 flex items-center justify-center text-xs" style={{ color: textColor }}>
                                Sin datos
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </WidgetErrorBoundary>
                </div>
              )
            })}
          </ResponsiveGrid>
        )}
      </div>

      {/* AI Analyst */}
      <DashboardAnalyst context={{ activeTab: activeTabId, kpis: analystKpis }} />

      {/* Info Modal */}
      {infoModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]"
          onClick={() => setInfoModal(null)}>
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
            style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
              <h3 className="font-semibold text-[#111827]">{infoModal.custom_title || infoModal.title}</h3>
              <button onClick={() => setInfoModal(null)} className="p-1 hover:bg-[#F3F4F6] rounded-md transition-colors">
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
                  to={infoModal.query_id
                    ? `/consultas/nueva?rerun=${infoModal.query_id}`
                    : `/consultas/nueva?q=${encodeURIComponent(infoModal.query_text || infoModal.sql || '')}`}
                  className="btn-primary text-sm inline-flex items-center gap-1.5 no-underline">
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
