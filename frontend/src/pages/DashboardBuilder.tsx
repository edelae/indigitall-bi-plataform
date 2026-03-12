import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import {
  Save, ArrowLeft, Plus, X, Info, Loader2,
  Sparkles, Send, GripVertical, LayoutTemplate,
  Type, Link as LinkIcon, Pencil, Palette, Eye, EyeOff,
  Calendar, AlignLeft, AlignCenter, AlignRight,
  Filter, ChevronDown as ChevronDownIcon,
} from 'lucide-react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import KpiCard from '../components/KpiCard'
import type { DashboardWidget, SavedQuery, ChartType, GridTemplate, DashboardGranularity, DashboardFilter } from '../types'
import {
  GRID_TEMPLATES, PRIMARY_COLOR, COLOR_PALETTES, FONT_FAMILIES, SIZE_PRESETS,
  CARD_STYLE_PRESETS, GRANULARITY_OPTIONS, transformSqlGranularity, getCardStyle,
  detectFilterableColumns, applyDashboardFilters,
} from '../types'
import {
  listQueries, getQuery, getDashboard,
  saveDashboard, updateDashboard, sendChat, saveQuery, executeSql,
} from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGrid = WidthProvider(Responsive)

// Grid constants — IDENTICAL between builder and view
const GRID_COLS = { lg: 12, md: 12, sm: 6, xs: 4 }
const GRID_BREAKPOINTS = { lg: 1200, md: 900, sm: 600, xs: 0 }
const GRID_ROW_HEIGHT = 80
const GRID_MARGIN: [number, number] = [8, 8]
const GRID_PADDING: [number, number] = [8, 8]

const TEXT_SIZE_CLASS: Record<string, string> = {
  xs: 'text-xs', sm: 'text-sm', base: 'text-base',
  lg: 'text-lg', xl: 'text-xl', '2xl': 'text-2xl',
}
const TEXT_SIZE_OPTIONS = [
  { value: 'xs', label: 'Muy pequeno' },
  { value: 'sm', label: 'Pequeno' },
  { value: 'base', label: 'Normal' },
  { value: 'lg', label: 'Grande' },
  { value: 'xl', label: 'Muy grande' },
  { value: '2xl', label: 'Extra grande' },
]
const KPI_STYLE_OPTIONS = [
  { value: 'minimal', label: 'Minimalista' },
  { value: 'accent', label: 'Con icono' },
  { value: 'progress', label: 'Con barra' },
]

// Chart type options for the AI assistant selector
const AI_CHART_OPTIONS: { value: ChartType; label: string }[] = [
  { value: 'bar', label: 'Barras' },
  { value: 'line', label: 'Linea' },
  { value: 'pie', label: 'Circular' },
  { value: 'area', label: 'Area' },
  { value: 'bar_horizontal', label: 'Barras H.' },
  { value: 'bar_stacked', label: 'Apiladas' },
  { value: 'scatter', label: 'Dispersion' },
  { value: 'combo', label: 'Combo' },
  { value: 'funnel', label: 'Embudo' },
  { value: 'kpi', label: 'KPI' },
  { value: 'table', label: 'Tabla' },
  { value: 'heatmap', label: 'Heatmap' },
]

interface AiPendingResult {
  question: string
  data: Record<string, any>[]
  columns: string[]
  suggestedChartType: string
  sql: string
  title: string
}

interface DashboardTab {
  id: string
  name: string
  widgets: DashboardWidget[]
}

export default function DashboardBuilder() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [dashboardId, setDashboardId] = useState<number | null>(null)

  const [tabs, setTabs] = useState<DashboardTab[]>([{ id: 'tab-1', name: 'General', widgets: [] }])
  const [activeTabId, setActiveTabId] = useState('tab-1')

  const [queries, setQueries] = useState<SavedQuery[]>([])
  const [querySearch, setQuerySearch] = useState('')

  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const [aiOpen, setAiOpen] = useState(false)
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiMessages, setAiMessages] = useState<{ role: string; content: string }[]>([])
  const [aiPendingResult, setAiPendingResult] = useState<AiPendingResult | null>(null)

  const [templateOpen, setTemplateOpen] = useState(false)
  const [activeTemplate, setActiveTemplate] = useState<GridTemplate | null>(null)
  const [templateVisible, setTemplateVisible] = useState(true) // toggle visibility

  const [sqlModal, setSqlModal] = useState<{ title: string; sql: string; queryText: string } | null>(null)
  const [editingTitle, setEditingTitle] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState<string | null>(null)
  const [editingTab, setEditingTab] = useState<string | null>(null)

  // Drag states
  const [dragOverCanvas, setDragOverCanvas] = useState(false)
  const [dragOverZone, setDragOverZone] = useState<number | null>(null)

  const canvasRef = useRef<HTMLDivElement>(null)

  // Granularity filter
  const [granularity, setGranularity] = useState<DashboardGranularity>('original')
  const [granLoading, setGranLoading] = useState(false)

  // Dashboard-level variable filters
  const [dashFilters, setDashFilters] = useState<DashboardFilter[]>([])
  const [filterPanelOpen, setFilterPanelOpen] = useState(false)
  const [filterLoading, setFilterLoading] = useState(false)

  // ─── Helpers ──────────────────────────────────────────────
  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0]
  const widgets = activeTab?.widgets || []

  const setWidgets = useCallback((updater: DashboardWidget[] | ((prev: DashboardWidget[]) => DashboardWidget[])) => {
    setTabs(prev => prev.map(t => {
      if (t.id !== activeTabId) return t
      const newWidgets = typeof updater === 'function' ? updater(t.widgets) : updater
      return { ...t, widgets: newWidgets }
    }))
  }, [activeTabId])

  // Check if a template zone is occupied by a widget
  const isZoneOccupied = useCallback((zone: { x: number; y: number; w: number; h: number }) => {
    return widgets.some(w => w.grid_x === zone.x && w.grid_y === zone.y && w.grid_w === zone.w && w.grid_h === zone.h)
  }, [widgets])

  // ─── Load data ─────────────────────────────────────────────
  useEffect(() => {
    listQueries({ limit: 100 }).then(r => setQueries(r.queries)).catch(() => {})
  }, [])

  useEffect(() => {
    const editId = searchParams.get('edit')
    const queryId = searchParams.get('query_id')
    if (editId) {
      getDashboard(parseInt(editId)).then(d => {
        setName(d.name)
        setDescription(d.description || '')
        setDashboardId(d.id)
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
              grid_i: w.grid_i || `widget-${Math.random().toString(36).slice(2)}`,
              grid_x: w.grid_x ?? 0, grid_y: w.grid_y ?? 0,
              grid_w: w.grid_w ?? w.width ?? 6, grid_h: w.grid_h ?? 4,
            })
          }
          const loadedTabs = Array.from(tabMap.values())
          setTabs(loadedTabs)
          setActiveTabId(loadedTabs[0].id)
        } else {
          const loaded = layout.map((w: DashboardWidget, i: number) => ({
            ...w,
            original_sql: w.sql || w.original_sql,
            grid_i: w.grid_i || `widget-${i}`,
            grid_x: w.grid_x ?? (i % 2) * 6, grid_y: w.grid_y ?? Math.floor(i / 2) * 4,
            grid_w: w.grid_w ?? w.width ?? 6, grid_h: w.grid_h ?? 4,
          }))
          setTabs([{ id: 'tab-1', name: 'General', widgets: loaded }])
          setActiveTabId('tab-1')
        }
      }).catch(() => {})
    } else if (queryId) {
      addQueryWidget(parseInt(queryId))
    }
  }, []) // eslint-disable-line

  // ─── Widget actions ────────────────────────────────────────
  const addQueryWidgetAt = async (queryId: number, x: number, y: number, w: number, h: number) => {
    try {
      const q = await getQuery(queryId)
      const viz = q.visualizations?.[0] || {} as Record<string, any>
      const chartType = viz.type || 'bar'
      const isKpi = chartType === 'kpi'
      const newWidget: DashboardWidget = {
        query_id: q.id,
        title: q.name.slice(0, 60),
        type: chartType, chart_type: chartType,
        width: w,
        data: q.result_data || [],
        columns: (q.result_columns || []).map(c => c.name),
        sql: q.generated_sql || '', query_text: q.query_text || '',
        grid_i: `widget-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        grid_x: x, grid_y: y, grid_w: w, grid_h: h,
        // Carry over chart personalization from saved query
        color_palette: viz.colorPalette,
        custom_x_label: viz.xLabel,
        custom_y_label: viz.yLabel,
        show_legend: viz.showLegend,
        font_family: viz.fontFamily,
        axis_font_size: viz.axisFontSize,
        legend_font_size: viz.legendFontSize,
        x_column: viz.xColumn,
        y_columns: viz.yColumns,
        group_by_column: viz.groupByColumn,
        ...(isKpi && q.result_data?.[0] ? {
          kpi_value: q.result_data[0][(q.result_columns || [])[1]?.name] || q.result_data[0][(q.result_columns || [])[0]?.name],
          kpi_label: q.name.slice(0, 40),
          kpi_style: viz.kpiStyle,
          kpi_color: viz.kpiColor,
          kpi_max_value: viz.kpiMaxValue,
        } : {}),
      }
      setWidgets(prev => [...prev, newWidget])
    } catch { /* ignore */ }
  }

  const addQueryWidget = (queryId: number) => addQueryWidgetAt(queryId, 0, 0, 6, 4)

  const addTitleBlock = () => {
    setWidgets(prev => [...prev, {
      title: 'Titulo de seccion', type: 'title', is_title_block: true,
      text_content: 'Escribe aqui el titulo o descripcion',
      width: 12, data: [], columns: [],
      grid_i: `title-${Date.now()}`, grid_x: 0, grid_y: 0, grid_w: 12, grid_h: 2,
    }])
  }

  const addTextCard = () => {
    setWidgets(prev => [...prev, {
      title: 'Tarjeta informativa', type: 'text_card',
      text_content: 'Informacion, enlaces o notas para el dashboard', text_url: '',
      width: 4, data: [], columns: [],
      grid_i: `text-${Date.now()}`, grid_x: 0, grid_y: 0, grid_w: 4, grid_h: 3,
    }])
  }

  const removeWidget = useCallback((gridI: string) => {
    setWidgets(prev => prev.filter(w => w.grid_i !== gridI))
  }, [setWidgets])

  const updateWidgetField = useCallback((gridI: string, field: string, value: any) => {
    setWidgets(prev => prev.map(w => w.grid_i === gridI ? { ...w, [field]: value } : w))
  }, [setWidgets])

  const handleLayoutChange = useCallback((layout: any[]) => {
    setWidgets(prev => {
      const updated = [...prev]
      for (const item of layout) {
        const idx = updated.findIndex(w => w.grid_i === item.i)
        if (idx >= 0) {
          updated[idx] = { ...updated[idx], grid_x: item.x, grid_y: item.y, grid_w: item.w, grid_h: item.h, width: item.w }
        }
      }
      return updated
    })
  }, [setWidgets])

  const startEditTitle = useCallback((gridI: string) => {
    setEditingTitle(gridI)
    requestAnimationFrame(() => {
      const input = document.querySelector(`[data-title-edit="${gridI}"]`) as HTMLInputElement
      if (input) { input.focus(); input.select() }
    })
  }, [])

  // ─── Granularity filter ────────────────────────────────────
  const hasDateTruncWidgets = tabs.some(t => t.widgets.some(w => (w.original_sql || w.sql || '').match(/DATE_TRUNC/i)))

  const handleGranularityChange = useCallback(async (gran: DashboardGranularity) => {
    setGranularity(gran)
    if (gran === 'original') {
      // Restore original SQL for all widgets
      setTabs(prev => prev.map(tab => ({
        ...tab,
        widgets: tab.widgets.map(w => {
          if (!w.original_sql) return w
          return { ...w, sql: w.original_sql }
        }),
      })))
      return
    }
    setGranLoading(true)
    const newTabs = await Promise.all(tabs.map(async tab => {
      const newWidgets = await Promise.all(tab.widgets.map(async w => {
        const origSql = w.original_sql || w.sql
        if (!origSql || !origSql.match(/DATE_TRUNC/i)) return w
        const transformed = transformSqlGranularity(origSql, gran)
        try {
          const res = await executeSql(transformed)
          return { ...w, data: res.data, columns: res.columns, sql: transformed, original_sql: origSql }
        } catch { return w }
      }))
      return { ...tab, widgets: newWidgets }
    }))
    setTabs(newTabs)
    setGranLoading(false)
  }, [tabs])

  // ─── Dashboard filters ──────────────────────────────────
  const availableFilterColumns = useMemo(() => {
    const allWidgets = tabs.flatMap(t => t.widgets)
    return detectFilterableColumns(allWidgets)
  }, [tabs])

  const addDashFilter = (col: string) => {
    if (dashFilters.some(f => f.column === col)) return
    const colInfo = availableFilterColumns.find(c => c.column === col)
    if (!colInfo) return
    setDashFilters(prev => [...prev, {
      id: `filter-${Date.now()}`,
      column: col,
      label: col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      values: colInfo.values,
      selected: [],
    }])
  }

  const removeDashFilter = (id: string) => {
    setDashFilters(prev => prev.filter(f => f.id !== id))
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
      // Reset to original data
      setTabs(prev => prev.map(tab => ({
        ...tab,
        widgets: tab.widgets.map(w => {
          if (!w.original_sql) return w
          return { ...w, sql: w.original_sql }
        }),
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

  // ─── Tab actions ──────────────────────────────────────────
  const addTab = () => {
    const t: DashboardTab = { id: `tab-${Date.now()}`, name: `Seccion ${tabs.length + 1}`, widgets: [] }
    setTabs(prev => [...prev, t])
    setActiveTabId(t.id)
  }
  const renameTab = (id: string, n: string) => setTabs(prev => prev.map(t => t.id === id ? { ...t, name: n } : t))
  const removeTab = (id: string) => {
    if (tabs.length <= 1) return
    const remaining = tabs.filter(t => t.id !== id)
    setTabs(remaining)
    if (activeTabId === id) setActiveTabId(remaining[0].id)
  }

  // ─── Save ─────────────────────────────────────────────────
  const handleSave = async () => {
    if (!name.trim()) { setFeedback({ type: 'error', text: 'Ingresa un nombre' }); return }
    const allWidgets = tabs.flatMap(t => t.widgets.map(w => ({ ...w, tab_id: t.id, tab_name: t.name })))
    if (!allWidgets.length) { setFeedback({ type: 'error', text: 'Agrega al menos un widget' }); return }
    setSaving(true)
    try {
      if (dashboardId) {
        await updateDashboard(dashboardId, allWidgets)
        setFeedback({ type: 'success', text: 'Tablero actualizado' })
      } else {
        const result = await saveDashboard({ name: name.trim(), description: description.trim(), layout: allWidgets })
        setDashboardId(result.id)
        setFeedback({ type: 'success', text: 'Tablero guardado' })
      }
    } catch { setFeedback({ type: 'error', text: 'Error guardando' }) }
    finally { setSaving(false); setTimeout(() => setFeedback(null), 4000) }
  }

  // ─── AI ────────────────────────────────────────────────────
  const executeAiQuestion = async (question: string) => {
    setAiLoading(true)
    try {
      const result = await sendChat(question)
      if (result.data?.length) {
        const suggestedType = result.chart_type || 'bar'
        setAiPendingResult({
          question,
          data: result.data,
          columns: result.columns,
          suggestedChartType: suggestedType,
          sql: result.query_details?.sql || '',
          title: result.query_details?.title || question.slice(0, 60),
        })
        setAiMessages(prev => [...prev, {
          role: 'assistant',
          content: `Encontre ${result.data.length} resultados. Selecciona el tipo de grafica que prefieres:`,
        }])
      } else {
        setAiMessages(prev => [...prev, { role: 'assistant', content: result.response || `Sin datos para: "${question}"` }])
      }
    } catch (err: any) { setAiMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }]) }
    finally { setAiLoading(false) }
  }

  const confirmAiWidget = async (chartType: ChartType) => {
    if (!aiPendingResult) return
    const { question, data, columns, sql, title } = aiPendingResult
    setAiPendingResult(null)

    try {
      // Save as a reusable query
      const saved = await saveQuery({
        name: title || question.slice(0, 60),
        query_text: question,
        data,
        columns,
        generated_sql: sql || null,
        chart_type: chartType,
      })

      const isKpi = chartType === 'kpi'

      // Create widget linked to the saved query
      setWidgets(prev => [...prev, {
        query_id: saved.id,
        title: title || question.slice(0, 60),
        type: chartType, chart_type: chartType,
        width: isKpi ? 3 : 6, data, columns,
        sql: sql || '', query_text: question,
        grid_i: `ai-${Date.now()}`, grid_x: 0, grid_y: 0,
        grid_w: isKpi ? 3 : 6, grid_h: isKpi ? 2 : 4,
        kpi_value: isKpi && data[0] ? data[0][columns[1]] || data[0][columns[0]] : undefined,
        kpi_label: isKpi ? (title || question.slice(0, 40)) : undefined,
      }])

      // Refresh queries sidebar so the new query appears
      listQueries({ limit: 100 }).then(r => setQueries(r.queries)).catch(() => {})

      setAiMessages(prev => [...prev, {
        role: 'system',
        content: `Grafica "${chartType}" agregada al tablero. Consulta guardada (ID: ${saved.id}).`,
      }])
    } catch (err: any) {
      setAiMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }])
    }
  }

  const handleAiSend = () => {
    if (!aiInput.trim()) return
    const m = aiInput.trim()
    setAiInput('')
    setAiPendingResult(null)
    setAiMessages(p => [...p, { role: 'user', content: m }])
    executeAiQuestion(m)
  }

  // ─── Drag from sidebar ────────────────────────────────────
  const handleDragStart = (e: React.DragEvent, queryId: number) => {
    e.dataTransfer.setData('application/query-id', String(queryId))
    e.dataTransfer.effectAllowed = 'copy'
  }

  const handleCanvasDragOver = (e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; setDragOverCanvas(true) }
  const handleCanvasDragLeave = () => { setDragOverCanvas(false); setDragOverZone(null) }
  const handleCanvasDrop = async (e: React.DragEvent) => {
    e.preventDefault(); setDragOverCanvas(false); setDragOverZone(null)
    const qid = e.dataTransfer.getData('application/query-id')
    if (qid) await addQueryWidget(parseInt(qid))
  }

  // Template zone drop handlers
  const handleZoneDragOver = (e: React.DragEvent, zoneIdx: number) => {
    e.preventDefault(); e.stopPropagation()
    e.dataTransfer.dropEffect = 'copy'
    setDragOverZone(zoneIdx)
  }
  const handleZoneDragLeave = (e: React.DragEvent) => {
    e.stopPropagation()
    setDragOverZone(null)
  }
  const handleZoneDrop = async (e: React.DragEvent, zone: { x: number; y: number; w: number; h: number }) => {
    e.preventDefault(); e.stopPropagation()
    setDragOverZone(null); setDragOverCanvas(false)
    const qid = e.dataTransfer.getData('application/query-id')
    if (qid && !isZoneOccupied(zone)) {
      await addQueryWidgetAt(parseInt(qid), zone.x, zone.y, zone.w, zone.h)
    }
  }

  // ─── Grid layout ──────────────────────────────────────────
  const gridLayout = widgets.map(w => ({ i: w.grid_i, x: w.grid_x, y: w.grid_y, w: w.grid_w, h: w.grid_h, minW: 1, minH: 1 }))

  const filteredQueries = querySearch
    ? queries.filter(q => q.name.toLowerCase().includes(querySearch.toLowerCase()))
    : queries

  // Calculate max Y from template for overlay height
  const templateMaxY = activeTemplate ? Math.max(...activeTemplate.zones.map(z => z.y + z.h)) : 8

  return (
    <div className="animate-fade-in">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex-1 max-w-lg">
          <input className="w-full text-lg font-bold border-0 border-b-2 border-transparent focus:border-primary outline-none pb-0.5 bg-transparent text-[#1F2937]"
            placeholder="Nombre del tablero..." value={name} onChange={e => setName(e.target.value)} />
          <input className="w-full text-xs text-[#6B7280] border-0 outline-none pb-0.5 mt-0.5 bg-transparent"
            placeholder="Descripcion (opcional)..." value={description} onChange={e => setDescription(e.target.value)} />
        </div>
        <div className="flex gap-1.5">
          <button onClick={() => setTemplateOpen(!templateOpen)} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5">
            <LayoutTemplate size={13} /> Templates
          </button>
          {activeTemplate && (
            <button onClick={() => setTemplateVisible(!templateVisible)} className="btn-secondary flex items-center gap-1 text-xs px-2 py-1.5" title={templateVisible ? 'Ocultar guia' : 'Mostrar guia'}>
              {templateVisible ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          )}
          <button onClick={() => setFilterPanelOpen(!filterPanelOpen)}
            className={`btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5 ${dashFilters.length > 0 ? 'ring-1 ring-primary/30' : ''}`}>
            <Filter size={13} /> Filtros {dashFilters.length > 0 && <span className="bg-primary text-white text-[9px] px-1.5 py-0.5 rounded-full">{dashFilters.length}</span>}
          </button>
          <button onClick={addTitleBlock} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5"><Type size={13} /> Titulo</button>
          <button onClick={addTextCard} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5"><LinkIcon size={13} /> Tarjeta</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-1 text-xs px-3 py-1.5">
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {dashboardId ? 'Actualizar' : 'Guardar'}
          </button>
          <Link to="/tableros" className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5 no-underline"><ArrowLeft size={13} /> Volver</Link>
        </div>
      </div>

      {feedback && (
        <div className={`mb-3 px-4 py-2 rounded-lg text-sm ${feedback.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {feedback.text}
          {feedback.type === 'success' && dashboardId && <Link to={`/tableros/saved/${dashboardId}`} className="ml-2 underline">Ver tablero</Link>}
        </div>
      )}

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

      {/* Dashboard Filters Panel */}
      {filterPanelOpen && (
        <div className="mb-3 bg-white border border-[#E5E7EB] rounded-lg shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E5E7EB] bg-[#F9FAFB]">
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-primary" />
              <h3 className="text-xs font-semibold text-[#374151]">Filtros del tablero</h3>
              <span className="text-[9px] text-[#9CA3AF]">Filtra todas las graficas a la vez</span>
            </div>
            <button onClick={() => setFilterPanelOpen(false)} className="p-0.5 hover:bg-gray-100 rounded"><X size={14} /></button>
          </div>
          <div className="p-3">
            {/* Available columns to add as filters */}
            {availableFilterColumns.length > 0 ? (
              <div className="mb-3">
                <p className="text-[10px] text-[#9CA3AF] uppercase tracking-wider mb-1.5">Columnas disponibles</p>
                <div className="flex flex-wrap gap-1">
                  {availableFilterColumns.map(c => {
                    const alreadyAdded = dashFilters.some(f => f.column === c.column)
                    return (
                      <button key={c.column}
                        disabled={alreadyAdded}
                        onClick={() => addDashFilter(c.column)}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all border ${
                          alreadyAdded
                            ? 'border-green-200 bg-green-50 text-green-600 cursor-default'
                            : 'border-[#E5E7EB] bg-white text-[#6B7280] hover:border-primary hover:text-primary hover:bg-primary/5 cursor-pointer'
                        }`}>
                        {alreadyAdded ? '✓ ' : '+ '}{c.column.replace(/_/g, ' ')}
                        <span className="text-[8px] ml-1 opacity-60">({c.values.length})</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              <p className="text-[10px] text-[#9CA3AF] mb-3">Agrega widgets con datos para ver columnas filtrables</p>
            )}

            {/* Active filters */}
            {dashFilters.length > 0 && (
              <div className="space-y-2">
                {dashFilters.map(filter => (
                  <div key={filter.id} className="border border-[#E5E7EB] rounded-lg p-2.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-semibold text-[#374151]">{filter.label}</span>
                      <div className="flex items-center gap-1">
                        {filter.selected.length > 0 && (
                          <button onClick={() => setDashFilters(prev => prev.map(f => f.id === filter.id ? { ...f, selected: [] } : f))}
                            className="text-[9px] text-primary hover:underline">Limpiar</button>
                        )}
                        <button onClick={() => removeDashFilter(filter.id)}
                          className="p-0.5 hover:bg-red-50 rounded text-[#9CA3AF] hover:text-red-500"><X size={10} /></button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                      {filter.values.map(val => {
                        const isSelected = filter.selected.includes(val)
                        return (
                          <button key={val}
                            onClick={() => toggleFilterValue(filter.id, val)}
                            className={`px-2 py-0.5 rounded text-[10px] transition-all border ${
                              isSelected
                                ? 'border-primary bg-primary text-white'
                                : 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280] hover:border-primary/30'
                            }`}>
                            {val}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
                <button onClick={applyFilters}
                  disabled={filterLoading}
                  className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5">
                  {filterLoading ? <Loader2 size={12} className="animate-spin" /> : <Filter size={12} />}
                  Aplicar filtros
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Active filter chips bar */}
      {dashFilters.some(f => f.selected.length > 0) && !filterPanelOpen && (
        <div className="flex items-center gap-2 mb-2 px-1 flex-wrap">
          <Filter size={12} className="text-[#9CA3AF]" />
          {dashFilters.filter(f => f.selected.length > 0).map(f => (
            <span key={f.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-medium rounded-lg">
              {f.label}: {f.selected.length === 1 ? f.selected[0] : `${f.selected.length} valores`}
              <button onClick={() => { setDashFilters(prev => prev.map(df => df.id === f.id ? { ...df, selected: [] } : df)); applyFilters() }}
                className="hover:bg-primary/20 rounded p-0.5"><X size={8} /></button>
            </span>
          ))}
          <button onClick={() => setFilterPanelOpen(true)} className="text-[10px] text-primary hover:underline">Editar</button>
        </div>
      )}

      {/* Templates panel */}
      {templateOpen && (
        <div className="mb-3 bg-white border border-[#E5E7EB] rounded-lg p-3 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-[#374151]">Plantillas de organizacion</h3>
            <div className="flex gap-1">
              {activeTemplate && <button onClick={() => { setActiveTemplate(null); setTemplateOpen(false) }} className="text-[9px] text-red-400 hover:text-red-600 px-1">Quitar plantilla</button>}
              <button onClick={() => setTemplateOpen(false)} className="p-0.5 hover:bg-gray-100 rounded"><X size={14} /></button>
            </div>
          </div>
          <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
            {GRID_TEMPLATES.map(tmpl => (
              <button key={tmpl.id}
                onClick={() => { setActiveTemplate(activeTemplate?.id === tmpl.id ? null : tmpl); setTemplateVisible(true); setTemplateOpen(false) }}
                className={`border rounded-lg p-1.5 hover:border-primary/50 transition-colors ${activeTemplate?.id === tmpl.id ? 'border-primary bg-primary/5' : 'border-[#E5E7EB]'}`}>
                <div className="relative w-full aspect-[3/2] bg-[#F3F4F6] rounded mb-0.5">
                  {tmpl.zones.map((z, i) => (
                    <div key={i} className="absolute bg-primary/20 border border-primary/30 rounded-sm"
                      style={{ left: `${(z.x / 12) * 100}%`, top: `${(z.y / templateMaxY) * 100}%`, width: `${(z.w / 12) * 100}%`, height: `${(z.h / templateMaxY) * 100}%` }} />
                  ))}
                </div>
                <p className="text-[9px] text-[#6B7280] text-center">{tmpl.name}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tabs bar — improved design (Prompt 5A) */}
      <div className="flex items-center gap-1 mb-0 border-b border-[#E5E7EB] bg-white px-2 py-1"
        onDragOver={e => e.preventDefault()}>
        {tabs.map((tab, idx) => (
          <div key={tab.id}
            draggable
            onDragStart={e => { e.dataTransfer.setData('tab-index', String(idx)) }}
            onDrop={e => {
              e.preventDefault()
              const fromIdx = parseInt(e.dataTransfer.getData('tab-index'))
              if (isNaN(fromIdx) || fromIdx === idx) return
              setTabs(prev => {
                const next = [...prev]
                const [moved] = next.splice(fromIdx, 1)
                next.splice(idx, 0, moved)
                return next
              })
            }}
            className={`group flex items-center gap-1.5 px-4 py-2 text-xs font-semibold cursor-pointer rounded-full transition-all select-none ${
              activeTabId === tab.id
                ? 'bg-primary text-white shadow-sm'
                : 'text-[#6B7280] hover:text-[#374151] hover:bg-gray-100'
            }`}
            onClick={() => setActiveTabId(tab.id)}
            onContextMenu={e => {
              e.preventDefault()
              setEditingTab(tab.id)
            }}>
            {editingTab === tab.id ? (
              <input className="text-xs font-semibold border-0 border-b border-white/50 outline-none bg-transparent w-24"
                style={{ color: activeTabId === tab.id ? 'white' : '#374151' }}
                value={tab.name} onChange={e => renameTab(tab.id, e.target.value)}
                onBlur={() => setEditingTab(null)} onKeyDown={e => e.key === 'Enter' && setEditingTab(null)}
                autoFocus onClick={e => e.stopPropagation()} />
            ) : (
              <span onDoubleClick={e => { e.stopPropagation(); setEditingTab(tab.id) }}>{tab.name}</span>
            )}
            {tabs.length > 1 && (
              <button onClick={e => { e.stopPropagation(); removeTab(tab.id) }}
                className={`opacity-0 group-hover:opacity-100 p-0.5 rounded-full transition-opacity ${
                  activeTabId === tab.id ? 'hover:bg-white/20' : 'hover:bg-red-100'
                }`} title="Eliminar">
                <X size={10} className={activeTabId === tab.id ? 'text-white/70' : 'text-red-400'} />
              </button>
            )}
          </div>
        ))}
        <button onClick={addTab} className="px-3 py-2 text-[#9CA3AF] hover:text-primary hover:bg-gray-100 rounded-full transition-all" title="Nueva seccion">
          <Plus size={14} />
        </button>
      </div>

      {/* Main: sidebar + canvas */}
      <div className="flex gap-0">
        {/* Sidebar */}
        <div className="w-56 flex-shrink-0 border-r border-[#E5E7EB] bg-white p-3 max-h-[calc(100vh-220px)] overflow-y-auto">
          <h3 className="text-[11px] font-semibold text-[#374151] mb-2 uppercase tracking-wider flex items-center gap-1">
            <GripVertical size={12} /> Consultas
          </h3>
          <input className="w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-2 outline-none focus:border-primary bg-[#F9FAFB]"
            placeholder="Buscar..." value={querySearch} onChange={e => setQuerySearch(e.target.value)} />
          {filteredQueries.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-[10px] text-[#9CA3AF]">No hay consultas</p>
              <Link to="/consultas/nueva" className="text-[10px] text-primary">Crear consulta</Link>
            </div>
          ) : filteredQueries.map(q => {
            const ct = q.visualizations?.[0]?.type || 'table'
            return (
              <div key={q.id} draggable onDragStart={e => handleDragStart(e, q.id)}
                className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg p-2 mb-1.5 hover:border-primary/30 transition-colors cursor-grab active:cursor-grabbing">
                <p className="text-[11px] font-medium text-[#374151] truncate">{q.name}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-[9px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">{ct.toUpperCase()}</span>
                  <span className="text-[9px] text-[#9CA3AF]">{q.result_row_count} filas</span>
                </div>
                <button onClick={() => addQueryWidget(q.id)}
                  className="w-full mt-1.5 text-[10px] py-1 rounded border border-primary/30 text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-1">
                  <Plus size={10} /> Agregar
                </button>
              </div>
            )
          })}
        </div>

        {/* Canvas — measured width via ResizeObserver */}
        <div ref={canvasRef}
          className={`flex-1 min-w-0 relative bg-[#F3F4F6] min-h-[500px] transition-colors ${dragOverCanvas && !activeTemplate ? 'ring-2 ring-primary/30 ring-inset bg-primary/5' : ''}`}
          onDragOver={!activeTemplate || !templateVisible ? handleCanvasDragOver : (e => { e.preventDefault(); setDragOverCanvas(true) })}
          onDragLeave={handleCanvasDragLeave}
          onDrop={!activeTemplate || !templateVisible ? handleCanvasDrop : (e => { e.preventDefault(); setDragOverCanvas(false) })}
        >
          {/* Template zone overlay — interactive drop targets */}
          {activeTemplate && templateVisible && (
            <div className="absolute z-10" style={{ inset: 8, pointerEvents: 'none' }}>
              {activeTemplate.zones.map((z, i) => {
                const occupied = isZoneOccupied(z)
                const isOver = dragOverZone === i && !occupied
                return (
                  <div key={i}
                    className={`absolute rounded-lg flex items-center justify-center transition-all ${
                      occupied
                        ? 'border-2 border-green-300/40 bg-green-50/20'
                        : isOver
                          ? 'border-2 border-primary bg-primary/10'
                          : 'border-2 border-dashed border-primary/20 bg-primary/[0.03]'
                    }`}
                    style={{
                      left: `${(z.x / 12) * 100}%`,
                      top: `${(z.y / templateMaxY) * 100}%`,
                      width: `${(z.w / 12) * 100}%`,
                      height: `${(z.h / templateMaxY) * 100}%`,
                      pointerEvents: 'auto',
                    }}
                    onDragOver={e => !occupied && handleZoneDragOver(e, i)}
                    onDragLeave={handleZoneDragLeave}
                    onDrop={e => handleZoneDrop(e, z)}
                  >
                    {occupied ? (
                      <span className="text-[9px] text-green-500/50 font-medium">Ocupado</span>
                    ) : isOver ? (
                      <span className="text-[10px] text-primary font-semibold">Soltar aqui</span>
                    ) : (
                      <span className="text-[9px] text-primary/25 font-medium">{z.w}x{z.h}</span>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Empty state */}
          {widgets.length === 0 && !dragOverCanvas && (
            <div className="border-2 border-dashed border-[#D1D5DB] rounded-xl min-h-[400px] flex items-center justify-center bg-white/50 m-2">
              <div className="text-center">
                <GripVertical size={40} className="text-[#D1D5DB] mx-auto mb-2" />
                <p className="text-[#6B7280] text-sm">Agrega consultas desde el panel lateral</p>
                <p className="text-[#9CA3AF] text-xs mt-1">Arrastra o usa el boton Agregar</p>
              </div>
            </div>
          )}

          {/* Drop hint when no template */}
          {dragOverCanvas && widgets.length === 0 && !activeTemplate && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
              <div className="bg-primary/10 border-2 border-dashed border-primary rounded-xl px-8 py-6 text-center">
                <Plus size={32} className="text-primary mx-auto mb-2" />
                <p className="text-primary font-medium text-sm">Suelta aqui para agregar</p>
              </div>
            </div>
          )}

          {/* Grid */}
          {widgets.length > 0 && (
            <ResponsiveGrid
              layouts={{ lg: gridLayout, md: gridLayout, sm: gridLayout, xs: gridLayout }}
              breakpoints={GRID_BREAKPOINTS}
              cols={GRID_COLS}
              rowHeight={GRID_ROW_HEIGHT}
              isDraggable isResizable
              compactType="vertical"
              margin={GRID_MARGIN}
              containerPadding={GRID_PADDING}
              onLayoutChange={handleLayoutChange}
              draggableCancel=".no-drag"
              measureBeforeMount
              style={{ minHeight: 400 }}
            >
              {widgets.map(w => {
                const cardSt = getCardStyle(w.card_style)
                const textColor = w.card_text_color || cardSt.color || '#111827'
                return (
                <div key={w.grid_i}>
                  <div className="rounded-lg h-full flex flex-col overflow-hidden" style={{ ...cardSt, ...(w.card_bg_color ? { background: w.card_bg_color, backgroundColor: w.card_bg_color } : {}) }}>
                    {/* Header — compact when hidden */}
                    <div className={`flex items-center justify-between px-3 flex-shrink-0 ${w.hide_header ? 'py-0.5 opacity-0 hover:opacity-100 transition-opacity absolute top-0 left-0 right-0 z-10' : 'py-1.5'}`}
                      style={{ borderBottom: w.hide_header ? 'none' : `1px solid ${textColor === '#FFFFFF' || textColor === '#F9FAFB' ? 'rgba(255,255,255,0.15)' : '#F0F1F5'}` }}>
                      {editingTitle === w.grid_i ? (
                        <input data-title-edit={w.grid_i}
                          className="no-drag font-semibold border-0 border-b border-primary outline-none flex-1 mr-2 bg-transparent"
                          style={{ fontSize: w.title_font_size || 13, fontFamily: w.font_family || 'Inter', color: textColor }}
                          value={w.custom_title || w.title}
                          onChange={e => updateWidgetField(w.grid_i, 'custom_title', e.target.value)}
                          onBlur={() => setEditingTitle(null)}
                          onKeyDown={e => { if (e.key === 'Enter') setEditingTitle(null) }}
                          autoFocus />
                      ) : (
                        <span className="font-semibold truncate flex-1 cursor-text"
                          style={{ fontSize: w.title_font_size || 13, fontFamily: w.font_family || 'Inter', color: textColor }}
                          onClick={() => startEditTitle(w.grid_i)} title="Clic para editar titulo">
                          {w.custom_title || w.title}
                        </span>
                      )}
                      <div className="no-drag flex gap-0.5 flex-shrink-0 relative">
                        <button onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                          onClick={e => { e.stopPropagation(); startEditTitle(w.grid_i) }}
                          className="p-1 rounded hover:bg-gray-100 transition-colors" title="Editar titulo">
                          <Pencil size={10} className="text-[#9CA3AF]" />
                        </button>
                        {(w.data?.length > 0 || w.is_title_block || w.type === 'text_card' || w.type === 'kpi') && (
                          <button onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                            onClick={e => { e.stopPropagation(); setSettingsOpen(settingsOpen === w.grid_i ? null : w.grid_i) }}
                            className="p-1 rounded hover:bg-gray-100 transition-colors" title="Configuracion">
                            <Palette size={10} className="text-[#9CA3AF]" />
                          </button>
                        )}
                        {w.sql && (
                          <button onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                            onClick={e => { e.stopPropagation(); setSqlModal({ title: w.title, sql: w.sql || '', queryText: w.query_text || '' }) }}
                            className="p-1 rounded hover:bg-gray-100 transition-colors" title="Ver SQL">
                            <Info size={10} className="text-[#9CA3AF]" />
                          </button>
                        )}
                        <button onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                          onClick={e => { e.stopPropagation(); removeWidget(w.grid_i) }}
                          className="p-1 rounded hover:bg-red-50 transition-colors" title="Eliminar">
                          <X size={10} className="text-[#9CA3AF] hover:text-red-500" />
                        </button>

                        {/* Settings dropdown */}
                        {settingsOpen === w.grid_i && (
                          <div className="no-drag absolute top-7 right-0 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-30 p-2 min-w-[220px] max-h-[420px] overflow-y-auto"
                            onMouseDown={e => e.stopPropagation()} onClick={e => e.stopPropagation()}>

                            {/* SIZE PRESETS (Prompt 2) — all widget types */}
                            <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Tamaño</p>
                            <div className="flex flex-wrap gap-1 mb-1.5">
                              {SIZE_PRESETS.map(sz => (
                                <button key={sz.label}
                                  onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'grid_w', sz.w); updateWidgetField(w.grid_i, 'grid_h', sz.h) }}
                                  className={`px-2 py-0.5 rounded text-[10px] transition-colors ${w.grid_w === sz.w && w.grid_h === sz.h ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'}`}>
                                  {sz.label}
                                </button>
                              ))}
                            </div>

                            {/* CHART TYPE SELECTOR (Prompt 5B) — chart widgets only */}
                            {w.data?.length > 0 && w.columns?.length >= 2 && w.type !== 'kpi' && !w.is_title_block && w.type !== 'text_card' && (
                              <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Tipo de gráfica</p>
                                <div className="grid grid-cols-4 gap-1 mb-1.5">
                                  {AI_CHART_OPTIONS.map(opt => (
                                    <button key={opt.value}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'chart_type', opt.value) }}
                                      className={`px-1 py-1 rounded text-[9px] text-center transition-colors ${(w.chart_type || 'bar') === opt.value ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'}`}>
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}

                            {(w.is_title_block || w.type === 'text_card') && (
                              <>
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Tamaño de texto</p>
                                <div className="flex flex-wrap gap-1 mb-1.5">
                                  {TEXT_SIZE_OPTIONS.map(opt => (
                                    <button key={opt.value}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'text_size', opt.value) }}
                                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${(w.text_size || (w.is_title_block ? 'lg' : 'sm')) === opt.value ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'}`}>
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                              </>
                            )}
                            {w.type === 'kpi' && (
                              <>
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Estilo de tarjeta</p>
                                <div className="flex flex-wrap gap-1 mb-1.5">
                                  {KPI_STYLE_OPTIONS.map(opt => (
                                    <button key={opt.value}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'kpi_style', opt.value) }}
                                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${(w.kpi_style || 'accent') === opt.value ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'}`}>
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                                {w.kpi_style === 'progress' && (
                                  <input className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-1 outline-none focus:border-primary"
                                    placeholder="Valor maximo (ej: 1000)" type="number" value={w.kpi_max_value || ''}
                                    onClick={e => e.stopPropagation()}
                                    onChange={e => updateWidgetField(w.grid_i, 'kpi_max_value', parseFloat(e.target.value) || undefined)} />
                                )}
                              </>
                            )}
                            {!w.is_title_block && w.type !== 'text_card' && (
                              <>
                                <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                                  <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Paleta</p>
                                  {Object.entries(COLOR_PALETTES).map(([key, pal]) => (
                                    <button key={key}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'color_palette', key) }}
                                      className={`w-full flex items-center gap-2 px-2 py-1 rounded text-[11px] hover:bg-[#F3F4F6] transition-colors ${w.color_palette === key ? 'bg-primary/10 font-semibold' : ''}`}>
                                      <div className="flex gap-0.5">
                                        {pal.colors.slice(0, 4).map((c, ci) => <div key={ci} className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />)}
                                      </div>
                                      <span>{pal.name}</span>
                                    </button>
                                  ))}
                                </div>
                                {w.type !== 'kpi' && (
                                  <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                                    <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Ejes</p>
                                    <input className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-1 outline-none focus:border-primary"
                                      placeholder="Nombre eje X" value={w.custom_x_label || ''}
                                      onClick={e => e.stopPropagation()} onChange={e => updateWidgetField(w.grid_i, 'custom_x_label', e.target.value)} />
                                    <input className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded outline-none focus:border-primary"
                                      placeholder="Nombre eje Y" value={w.custom_y_label || ''}
                                      onClick={e => e.stopPropagation()} onChange={e => updateWidgetField(w.grid_i, 'custom_y_label', e.target.value)} />
                                  </div>
                                )}
                              </>
                            )}

                            {/* FONT CUSTOMIZATION (Prompt 4) — all widget types */}
                            <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                              <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Tipografía</p>
                              <select className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-1 outline-none focus:border-primary bg-white"
                                value={w.font_family || ''} onClick={e => e.stopPropagation()}
                                onChange={e => updateWidgetField(w.grid_i, 'font_family', e.target.value || undefined)}>
                                <option value="">Por defecto (Inter)</option>
                                {FONT_FAMILIES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                              </select>
                              <div className="flex gap-1">
                                <input className="no-drag w-1/2 text-[11px] px-2 py-1 border border-[#E5E7EB] rounded outline-none focus:border-primary"
                                  type="number" min="8" max="48" placeholder="Título px" value={w.title_font_size || ''}
                                  onClick={e => e.stopPropagation()}
                                  onChange={e => updateWidgetField(w.grid_i, 'title_font_size', parseInt(e.target.value) || undefined)} />
                                <input className="no-drag w-1/2 text-[11px] px-2 py-1 border border-[#E5E7EB] rounded outline-none focus:border-primary"
                                  type="number" min="8" max="48" placeholder="Ejes px" value={w.axis_font_size || ''}
                                  onClick={e => e.stopPropagation()}
                                  onChange={e => updateWidgetField(w.grid_i, 'axis_font_size', parseInt(e.target.value) || undefined)} />
                              </div>
                            </div>

                            {/* CARD STYLE PRESETS */}
                            <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                              <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Estilo de tarjeta</p>
                              <div className="grid grid-cols-3 gap-1 mb-1.5">
                                {CARD_STYLE_PRESETS.map(preset => (
                                  <button key={preset.id}
                                    onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'card_style', preset.id) }}
                                    className={`px-1 py-1 rounded text-[9px] text-center transition-all border ${
                                      (w.card_style || 'default') === preset.id
                                        ? 'border-primary ring-1 ring-primary/30'
                                        : 'border-[#E5E7EB] hover:border-primary/30'
                                    }`}
                                    style={{
                                      background: preset.bg.includes('gradient') ? preset.bg : preset.bg,
                                      color: preset.text,
                                      ...(preset.accent ? { borderLeft: preset.accent } : {}),
                                    }}>
                                    {preset.label}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* CUSTOM CARD COLORS */}
                            <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                              <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Colores personalizados</p>
                              <div className="flex gap-1 mb-1">
                                <div className="flex-1">
                                  <label className="text-[8px] text-[#9CA3AF] px-1">Fondo</label>
                                  <input className="no-drag w-full h-6 rounded cursor-pointer border border-[#E5E7EB]"
                                    type="color" value={w.card_bg_color || '#FFFFFF'}
                                    onClick={e => e.stopPropagation()}
                                    onChange={e => updateWidgetField(w.grid_i, 'card_bg_color', e.target.value)} />
                                </div>
                                <div className="flex-1">
                                  <label className="text-[8px] text-[#9CA3AF] px-1">Texto</label>
                                  <input className="no-drag w-full h-6 rounded cursor-pointer border border-[#E5E7EB]"
                                    type="color" value={w.card_text_color || '#111827'}
                                    onClick={e => e.stopPropagation()}
                                    onChange={e => updateWidgetField(w.grid_i, 'card_text_color', e.target.value)} />
                                </div>
                                {(w.card_bg_color || w.card_text_color) && (
                                  <button onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'card_bg_color', undefined); updateWidgetField(w.grid_i, 'card_text_color', undefined) }}
                                    className="self-end px-1 py-0.5 text-[8px] text-red-400 hover:text-red-600">Reset</button>
                                )}
                              </div>
                            </div>

                            {/* HIDE HEADER / TEXT ALIGN */}
                            <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                              <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Opciones</p>
                              <label className="flex items-center gap-1.5 px-1 mb-1 cursor-pointer" onClick={e => e.stopPropagation()}>
                                <input type="checkbox" className="no-drag w-3 h-3 rounded border-[#D1D5DB] accent-primary"
                                  checked={!!w.hide_header}
                                  onChange={e => updateWidgetField(w.grid_i, 'hide_header', e.target.checked)} />
                                <span className="text-[10px] text-[#6B7280]">Ocultar encabezado</span>
                              </label>
                              <div className="flex gap-1 px-1">
                                {([['left', AlignLeft], ['center', AlignCenter], ['right', AlignRight]] as const).map(([align, Icon]) => (
                                  <button key={align}
                                    onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'text_align', align) }}
                                    className={`p-1 rounded transition-colors ${(w.text_align || 'left') === align ? 'bg-primary/10 text-primary' : 'text-[#9CA3AF] hover:bg-gray-100'}`}
                                    title={align}>
                                    <Icon size={12} />
                                  </button>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
                      {w.is_title_block ? (
                        <div className="no-drag flex items-center justify-center flex-1 px-4"
                          style={{ textAlign: w.text_align || 'center' }}>
                          <input className={`${TEXT_SIZE_CLASS[w.text_size || 'lg']} font-bold w-full bg-transparent border-0 outline-none`}
                            style={{ color: textColor, textAlign: w.text_align || 'center' }}
                            value={w.text_content || ''} onChange={e => updateWidgetField(w.grid_i, 'text_content', e.target.value)}
                            placeholder="Titulo de seccion..." />
                        </div>
                      ) : w.type === 'text_card' ? (
                        <div className="no-drag flex-1 flex flex-col gap-1 p-2" style={{ textAlign: w.text_align || 'left' }}>
                          <textarea className={`flex-1 ${TEXT_SIZE_CLASS[w.text_size || 'sm']} bg-transparent border-0 outline-none resize-none`}
                            style={{ color: textColor }}
                            value={w.text_content || ''} onChange={e => updateWidgetField(w.grid_i, 'text_content', e.target.value)}
                            placeholder="Texto informativo..." />
                          <input className="text-xs text-primary bg-transparent border-0 border-b border-[#E5E7EB] outline-none"
                            value={w.text_url || ''} onChange={e => updateWidgetField(w.grid_i, 'text_url', e.target.value)}
                            placeholder="URL (opcional)" />
                        </div>
                      ) : w.type === 'kpi' && w.kpi_value !== undefined ? (
                        <div className="flex-1 flex items-center justify-center">
                          <KpiCard label={w.kpi_label || w.title} value={w.kpi_value} color={w.kpi_color || PRIMARY_COLOR}
                            delta={w.kpi_delta} kpiStyle={w.kpi_style || 'accent'} maxValue={w.kpi_max_value} />
                        </div>
                      ) : w.data?.length && w.columns?.length >= 2 ? (
                        <div className="flex-1" style={{ position: 'relative', minHeight: 0 }}>
                          <div style={{ position: 'absolute', inset: 4 }}>
                            <ChartWidget data={w.data} columns={w.columns}
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
                      ) : w.data?.length ? (
                        <div className="flex-1 text-xs overflow-auto p-2">
                          <table className="w-full">
                            <thead><tr className="bg-[#F9FAFB]">
                              {w.columns.map(c => <th key={c} className="px-2 py-1 text-left text-[10px] font-semibold text-[#6B7280]">{c}</th>)}
                            </tr></thead>
                            <tbody>
                              {w.data.slice(0, 8).map((row, ri) => (
                                <tr key={ri} className="border-b border-[#F3F4F6]">
                                  {w.columns.map(c => <td key={c} className="px-2 py-1 text-[10px] truncate max-w-[120px]">{String(row[c] ?? '')}</td>)}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="flex-1 flex items-center justify-center text-xs text-[#9CA3AF]">Sin datos</div>
                      )}
                    </div>
                  </div>
                </div>
              )})}
            </ResponsiveGrid>
          )}
        </div>
      </div>

      {/* AI FAB */}
      {createPortal(
        <>
          <button onClick={() => setAiOpen(!aiOpen)}
            className="btn-primary rounded-full py-2.5 px-5 shadow-lg flex items-center gap-2"
            style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999 }}>
            <Sparkles size={16} /> Asistente IA
          </button>
          {aiOpen && (
            <div className="flex flex-col border-l border-[#E5E7EB]"
              style={{ position: 'fixed', top: 0, right: 0, width: 384, height: '100vh', background: 'white', boxShadow: '-4px 0 24px rgba(0,0,0,0.1)', zIndex: 10000 }}>
              <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
                <h3 className="font-semibold text-sm text-[#1F2937]">Asistente IA para Tableros</h3>
                <button onClick={() => setAiOpen(false)} className="p-1 hover:bg-gray-100 rounded"><X size={16} /></button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <div className="bg-[#F3F4F6] p-3 rounded-lg text-xs text-[#6B7280]">
                  <Sparkles size={14} className="text-primary inline mr-1" />
                  Describe que metricas quieres y las agregare al canvas.
                </div>
                {aiMessages.map((m, i) => (
                  <div key={i} className={`p-2 rounded-lg text-xs ${
                    m.role === 'user' ? 'bg-primary text-white ml-8' :
                    m.role === 'system' && m.content.startsWith('Grafica') ? 'bg-green-50 text-green-700' :
                    m.role === 'system' && m.content.startsWith('Error') ? 'bg-red-50 text-red-700' :
                    'bg-[#F3F4F6] text-[#374151]'
                  }`}>{m.content}</div>
                ))}

                {/* Chart type selector — shown when AI has pending results */}
                {aiPendingResult && (
                  <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg animate-fade-in">
                    <p className="text-[11px] text-[#374151] mb-2 font-medium">Tipo de grafica:</p>
                    <div className="grid grid-cols-4 gap-1">
                      {AI_CHART_OPTIONS.map(opt => (
                        <button
                          key={opt.value}
                          onClick={() => confirmAiWidget(opt.value)}
                          className={`px-1.5 py-1.5 rounded-lg text-center transition-colors border ${
                            aiPendingResult.suggestedChartType === opt.value
                              ? 'border-primary bg-primary/10 text-primary font-semibold'
                              : 'border-[#E5E7EB] bg-white hover:bg-primary/5 text-[#6B7280]'
                          }`}
                        >
                          <p className="text-[10px] leading-tight">{opt.label}</p>
                        </button>
                      ))}
                    </div>
                    <p className="text-[9px] text-[#9CA3AF] mt-1.5">
                      Sugerido: <span className="font-medium text-primary">{aiPendingResult.suggestedChartType}</span>
                      {' '}({aiPendingResult.data.length} filas)
                    </p>
                  </div>
                )}

                {aiLoading && <div className="flex items-center gap-2 text-xs text-[#9CA3AF]"><Loader2 size={12} className="animate-spin" /> Ejecutando...</div>}
              </div>
              <div className="p-4 border-t border-[#E5E7EB]">
                <div className="flex gap-2">
                  <input className="flex-1 text-sm px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none focus:border-primary"
                    placeholder="Ej: Agrega KPI con total de mensajes" value={aiInput}
                    onChange={e => setAiInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAiSend()} />
                  <button onClick={handleAiSend} className="btn-primary p-2 rounded-lg" disabled={aiLoading}><Send size={14} /></button>
                </div>
              </div>
            </div>
          )}
        </>, document.body
      )}

      {/* SQL Modal */}
      {sqlModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setSqlModal(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
              <h3 className="font-semibold text-[#1F2937]">{sqlModal.title}</h3>
              <button onClick={() => setSqlModal(null)} className="p-1 hover:bg-gray-100 rounded"><X size={16} /></button>
            </div>
            <div className="p-4 space-y-3">
              {sqlModal.queryText && <div><p className="text-xs font-semibold text-[#6B7280] mb-1">Pregunta original</p><p className="text-sm text-[#374151]">{sqlModal.queryText}</p></div>}
              {sqlModal.sql && <div><p className="text-xs font-semibold text-[#6B7280] mb-1">SQL generado</p><pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-lg text-xs overflow-x-auto font-mono whitespace-pre-wrap">{sqlModal.sql}</pre></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
