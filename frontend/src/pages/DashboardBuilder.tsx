import { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import {
  Save, ArrowLeft, Plus, X, Info, Loader2,
  Sparkles, Send, GripVertical, LayoutTemplate,
  Type, Link as LinkIcon, Pencil, Palette,
} from 'lucide-react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import KpiCard from '../components/KpiCard'
import type { DashboardWidget, SavedQuery, ChartType, GridTemplate } from '../types'
import { GRID_TEMPLATES, PRIMARY_COLOR, COLOR_PALETTES } from '../types'
import {
  listQueries, getQuery, getDashboard,
  saveDashboard, updateDashboard, sendChat,
} from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

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

// ─── Tab / Section Types ───────────────────────────────────────────
interface DashboardTab {
  id: string
  name: string
  widgets: DashboardWidget[]
}

export default function DashboardBuilder() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // Dashboard metadata
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [dashboardId, setDashboardId] = useState<number | null>(null)

  // Tabs / sections
  const [tabs, setTabs] = useState<DashboardTab[]>([
    { id: 'tab-1', name: 'General', widgets: [] },
  ])
  const [activeTabId, setActiveTabId] = useState('tab-1')

  // Queries sidebar
  const [queries, setQueries] = useState<SavedQuery[]>([])
  const [querySearch, setQuerySearch] = useState('')

  // Save state
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // AI Assistant
  const [aiOpen, setAiOpen] = useState(false)
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiMessages, setAiMessages] = useState<{ role: string; content: string }[]>([])

  // Templates
  const [templateOpen, setTemplateOpen] = useState(false)
  const [activeTemplate, setActiveTemplate] = useState<GridTemplate | null>(null)

  // SQL Modal
  const [sqlModal, setSqlModal] = useState<{ title: string; sql: string; queryText: string } | null>(null)

  // Edit widget title — PROMPT 2
  const [editingTitle, setEditingTitle] = useState<string | null>(null)
  // Widget settings dropdown
  const [settingsOpen, setSettingsOpen] = useState<string | null>(null)
  // Tab rename
  const [editingTab, setEditingTab] = useState<string | null>(null)

  // Drag from sidebar — PROMPT 4
  const [dragOverCanvas, setDragOverCanvas] = useState(false)

  // Canvas ref
  const canvasRef = useRef<HTMLDivElement>(null)

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
              grid_i: w.grid_i || `widget-${Math.random().toString(36).slice(2)}`,
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
          const loaded = layout.map((w: DashboardWidget, i: number) => ({
            ...w,
            grid_i: w.grid_i || `widget-${i}`,
            grid_x: w.grid_x ?? (i % 2) * 6,
            grid_y: w.grid_y ?? Math.floor(i / 2) * 4,
            grid_w: w.grid_w ?? w.width ?? 6,
            grid_h: w.grid_h ?? 4,
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
  const addQueryWidget = async (queryId: number) => {
    try {
      const q = await getQuery(queryId)
      const chartType = q.visualizations?.[0]?.type || 'bar'
      const isKpi = chartType === 'kpi'
      const newWidget: DashboardWidget = {
        query_id: q.id,
        title: q.name.slice(0, 60),
        type: chartType,
        chart_type: chartType,
        width: isKpi ? 3 : 6,
        data: q.result_data || [],
        columns: (q.result_columns || []).map(c => c.name),
        sql: q.generated_sql || '',
        query_text: q.query_text || '',
        grid_i: `widget-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        grid_x: 0,
        grid_y: 0,
        grid_w: isKpi ? 3 : 6,
        grid_h: isKpi ? 2 : 4,
        ...(isKpi && q.result_data?.[0] ? {
          kpi_value: q.result_data[0][(q.result_columns || [])[1]?.name] || q.result_data[0][(q.result_columns || [])[0]?.name],
          kpi_label: q.name.slice(0, 40),
        } : {}),
      }
      setWidgets(prev => [...prev, newWidget])
    } catch { /* ignore */ }
  }

  const addTitleBlock = () => {
    const newWidget: DashboardWidget = {
      title: 'Titulo de seccion',
      type: 'title',
      is_title_block: true,
      text_content: 'Escribe aqui el titulo o descripcion',
      width: 12,
      data: [],
      columns: [],
      grid_i: `title-${Date.now()}`,
      grid_x: 0,
      grid_y: 0,
      grid_w: 12,
      grid_h: 2,
    }
    setWidgets(prev => [...prev, newWidget])
  }

  const addTextCard = () => {
    const newWidget: DashboardWidget = {
      title: 'Tarjeta informativa',
      type: 'text_card',
      text_content: 'Informacion, enlaces o notas para el dashboard',
      text_url: '',
      width: 4,
      data: [],
      columns: [],
      grid_i: `text-${Date.now()}`,
      grid_x: 0,
      grid_y: 0,
      grid_w: 4,
      grid_h: 3,
    }
    setWidgets(prev => [...prev, newWidget])
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
          updated[idx] = {
            ...updated[idx],
            grid_x: item.x, grid_y: item.y, grid_w: item.w, grid_h: item.h, width: item.w,
          }
        }
      }
      return updated
    })
  }, [setWidgets])

  // PROMPT 2 — start editing title
  const startEditTitle = useCallback((gridI: string) => {
    setEditingTitle(gridI)
    // Use requestAnimationFrame to ensure the input is rendered before focusing
    requestAnimationFrame(() => {
      const input = document.querySelector(`[data-title-edit="${gridI}"]`) as HTMLInputElement
      if (input) { input.focus(); input.select() }
    })
  }, [])

  // ─── Tab actions ──────────────────────────────────────────
  const addTab = () => {
    const newTab: DashboardTab = {
      id: `tab-${Date.now()}`,
      name: `Seccion ${tabs.length + 1}`,
      widgets: [],
    }
    setTabs(prev => [...prev, newTab])
    setActiveTabId(newTab.id)
  }

  const renameTab = (tabId: string, newName: string) => {
    setTabs(prev => prev.map(t => t.id === tabId ? { ...t, name: newName } : t))
  }

  const removeTab = (tabId: string) => {
    if (tabs.length <= 1) return
    const remaining = tabs.filter(t => t.id !== tabId)
    setTabs(remaining)
    if (activeTabId === tabId) setActiveTabId(remaining[0].id)
  }

  // ─── Save ─────────────────────────────────────────────────
  const handleSave = async () => {
    if (!name.trim()) { setFeedback({ type: 'error', text: 'Ingresa un nombre' }); return }
    const allWidgets = tabs.flatMap(t =>
      t.widgets.map(w => ({ ...w, tab_id: t.id, tab_name: t.name }))
    )
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
    } catch {
      setFeedback({ type: 'error', text: 'Error guardando' })
    } finally {
      setSaving(false)
      setTimeout(() => setFeedback(null), 4000)
    }
  }

  // ─── AI Assistant ─────────────────────────────────────────
  const executeAiQuestion = async (question: string) => {
    setAiLoading(true)
    try {
      const result = await sendChat(question)
      if (result.data?.length) {
        const isKpi = result.chart_type === 'kpi' || question.toLowerCase().includes('kpi') || question.toLowerCase().includes('tarjeta')
        const newWidget: DashboardWidget = {
          title: result.query_details?.title || question.slice(0, 60),
          type: isKpi ? 'kpi' : (result.chart_type || 'bar'),
          chart_type: result.chart_type || 'bar',
          width: isKpi ? 3 : 6,
          data: result.data,
          columns: result.columns,
          sql: result.query_details?.sql || '',
          query_text: question,
          grid_i: `ai-${Date.now()}`,
          grid_x: 0,
          grid_y: 0,
          grid_w: isKpi ? 3 : 6,
          grid_h: isKpi ? 2 : 4,
          kpi_value: isKpi && result.data[0] ? result.data[0][result.columns[1]] || result.data[0][result.columns[0]] : undefined,
          kpi_label: isKpi ? (result.query_details?.title || question.slice(0, 40)) : undefined,
        }
        setWidgets(prev => [...prev, newWidget])
        setAiMessages(prev => [...prev, { role: 'system', content: `Agregado: "${question}" (${result.data.length} filas)` }])
      } else {
        setAiMessages(prev => [...prev, { role: 'assistant', content: result.response || `Sin datos para: "${question}"` }])
      }
    } catch (err: any) {
      setAiMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }])
    } finally {
      setAiLoading(false)
    }
  }

  const handleAiSend = () => {
    if (!aiInput.trim()) return
    const msg = aiInput.trim()
    setAiInput('')
    setAiMessages(prev => [...prev, { role: 'user', content: msg }])
    executeAiQuestion(msg)
  }

  // ─── PROMPT 4: Drag from sidebar ─────────────────────────
  const handleDragStart = (e: React.DragEvent, queryId: number) => {
    e.dataTransfer.setData('text/plain', String(queryId))
    e.dataTransfer.effectAllowed = 'copy'
  }

  const handleCanvasDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    setDragOverCanvas(true)
  }

  const handleCanvasDragLeave = () => {
    setDragOverCanvas(false)
  }

  const handleCanvasDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setDragOverCanvas(false)
    const queryId = e.dataTransfer.getData('text/plain')
    if (queryId) {
      await addQueryWidget(parseInt(queryId))
    }
  }

  // ─── Grid layout ──────────────────────────────────────────
  const gridLayout = widgets.map(w => ({
    i: w.grid_i,
    x: w.grid_x,
    y: w.grid_y,
    w: w.grid_w,
    h: w.grid_h,
    minW: 1,
    minH: 1,
  }))

  const filteredQueries = querySearch
    ? queries.filter(q => q.name.toLowerCase().includes(querySearch.toLowerCase()))
    : queries

  return (
    <div className="animate-fade-in">
      {/* ─── Top bar ─── */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex-1 max-w-lg">
          <input
            className="w-full text-lg font-bold border-0 border-b-2 border-transparent focus:border-primary outline-none pb-0.5 bg-transparent text-[#1F2937]"
            placeholder="Nombre del tablero..."
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            className="w-full text-xs text-[#6B7280] border-0 outline-none pb-0.5 mt-0.5 bg-transparent"
            placeholder="Descripcion (opcional)..."
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
        </div>
        <div className="flex gap-1.5">
          <button onClick={() => setTemplateOpen(!templateOpen)} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5">
            <LayoutTemplate size={13} /> Templates
          </button>
          <button onClick={addTitleBlock} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5">
            <Type size={13} /> Titulo
          </button>
          <button onClick={addTextCard} className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5">
            <LinkIcon size={13} /> Tarjeta
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-1 text-xs px-3 py-1.5">
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {dashboardId ? 'Actualizar' : 'Guardar'}
          </button>
          <Link to="/tableros" className="btn-secondary flex items-center gap-1 text-xs px-2.5 py-1.5 no-underline">
            <ArrowLeft size={13} /> Volver
          </Link>
        </div>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`mb-3 px-4 py-2 rounded-lg text-sm ${feedback.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {feedback.text}
          {feedback.type === 'success' && dashboardId && (
            <Link to={`/tableros/saved/${dashboardId}`} className="ml-2 underline">Ver tablero</Link>
          )}
        </div>
      )}

      {/* Templates panel */}
      {templateOpen && (
        <div className="mb-3 bg-white border border-[#E5E7EB] rounded-lg p-3 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-[#374151]">Plantillas de organizacion</h3>
            <button onClick={() => setTemplateOpen(false)} className="p-0.5 hover:bg-gray-100 rounded"><X size={14} /></button>
          </div>
          <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
            {GRID_TEMPLATES.map(tmpl => (
              <button
                key={tmpl.id}
                onClick={() => { setActiveTemplate(activeTemplate?.id === tmpl.id ? null : tmpl); setTemplateOpen(false) }}
                className={`border rounded-lg p-1.5 hover:border-primary/50 transition-colors ${activeTemplate?.id === tmpl.id ? 'border-primary bg-primary/5' : 'border-[#E5E7EB]'}`}
              >
                <div className="relative w-full aspect-[3/2] bg-[#F3F4F6] rounded mb-0.5">
                  {tmpl.zones.map((z, i) => (
                    <div key={i} className="absolute bg-primary/20 border border-primary/30 rounded-sm"
                      style={{ left: `${(z.x / 12) * 100}%`, top: `${(z.y / 8) * 100}%`, width: `${(z.w / 12) * 100}%`, height: `${(z.h / 8) * 100}%` }}
                    />
                  ))}
                </div>
                <p className="text-[9px] text-[#6B7280] text-center">{tmpl.name}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─── Tabs bar (sections) ─── */}
      <div className="flex items-center gap-0.5 mb-0 border-b border-[#E5E7EB] bg-white px-1">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`group flex items-center gap-1 px-3 py-1.5 text-xs font-medium cursor-pointer border-b-2 transition-colors ${
              activeTabId === tab.id
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-[#6B7280] hover:text-[#374151] hover:bg-gray-50'
            }`}
            onClick={() => setActiveTabId(tab.id)}
          >
            {editingTab === tab.id ? (
              <input
                className="text-xs font-medium border-0 border-b border-primary outline-none bg-transparent w-20"
                value={tab.name}
                onChange={e => renameTab(tab.id, e.target.value)}
                onBlur={() => setEditingTab(null)}
                onKeyDown={e => e.key === 'Enter' && setEditingTab(null)}
                autoFocus
                onClick={e => e.stopPropagation()}
              />
            ) : (
              <span onDoubleClick={(e) => { e.stopPropagation(); setEditingTab(tab.id) }}>{tab.name}</span>
            )}
            {tabs.length > 1 && (
              <button
                onClick={e => { e.stopPropagation(); removeTab(tab.id) }}
                className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-100 rounded transition-opacity"
                title="Eliminar seccion"
              >
                <X size={10} className="text-red-400" />
              </button>
            )}
          </div>
        ))}
        <button onClick={addTab} className="px-2 py-1.5 text-[#9CA3AF] hover:text-primary transition-colors" title="Nueva seccion">
          <Plus size={14} />
        </button>
      </div>

      {/* ─── Main: sidebar + canvas ─── */}
      <div className="flex gap-0">
        {/* Sidebar: queries — PROMPT 4: draggable items */}
        <div className="w-56 flex-shrink-0 border-r border-[#E5E7EB] bg-white p-3 max-h-[calc(100vh-220px)] overflow-y-auto">
          <h3 className="text-[11px] font-semibold text-[#374151] mb-2 uppercase tracking-wider flex items-center gap-1">
            <GripVertical size={12} /> Consultas
          </h3>
          <input
            className="w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-2 outline-none focus:border-primary bg-[#F9FAFB]"
            placeholder="Buscar..."
            value={querySearch}
            onChange={e => setQuerySearch(e.target.value)}
          />
          {filteredQueries.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-[10px] text-[#9CA3AF]">No hay consultas</p>
              <Link to="/consultas/nueva" className="text-[10px] text-primary">Crear consulta</Link>
            </div>
          ) : (
            filteredQueries.map(q => {
              const chartType = q.visualizations?.[0]?.type || 'table'
              return (
                <div
                  key={q.id}
                  draggable
                  onDragStart={e => handleDragStart(e, q.id)}
                  className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg p-2 mb-1.5 hover:border-primary/30 transition-colors cursor-grab active:cursor-grabbing"
                >
                  <p className="text-[11px] font-medium text-[#374151] truncate">{q.name}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="text-[9px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">{chartType.toUpperCase()}</span>
                    <span className="text-[9px] text-[#9CA3AF]">{q.result_row_count} filas</span>
                  </div>
                  <button
                    onClick={() => addQueryWidget(q.id)}
                    className="w-full mt-1.5 text-[10px] py-1 rounded border border-primary/30 text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-1"
                  >
                    <Plus size={10} /> Agregar
                  </button>
                </div>
              )
            })
          )}
        </div>

        {/* Canvas — PROMPT 1 FIX: containerPadding matches view mode */}
        <div
          ref={canvasRef}
          className={`flex-1 min-w-0 relative bg-[#F3F4F6] min-h-[500px] transition-colors ${
            dragOverCanvas ? 'bg-primary/5 ring-2 ring-primary/30 ring-inset' : ''
          }`}
          style={{ padding: 0 }}
          onDragOver={handleCanvasDragOver}
          onDragLeave={handleCanvasDragLeave}
          onDrop={handleCanvasDrop}
        >
          {/* Template guide overlay */}
          {activeTemplate && (
            <div className="absolute inset-2 z-0 pointer-events-none">
              {activeTemplate.zones.map((z, i) => (
                <div
                  key={i}
                  className="absolute border-2 border-dashed border-primary/15 bg-primary/[0.03] rounded-lg flex items-center justify-center"
                  style={{
                    left: `${(z.x / 12) * 100}%`,
                    top: `${(z.y / 8) * 100}%`,
                    width: `${(z.w / 12) * 100}%`,
                    height: `${(z.h / 8) * 100}%`,
                  }}
                >
                  <span className="text-[9px] text-primary/20 font-medium">{z.w}x{z.h}</span>
                </div>
              ))}
            </div>
          )}

          {/* Drop hint */}
          {dragOverCanvas && widgets.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
              <div className="bg-primary/10 border-2 border-dashed border-primary rounded-xl px-8 py-6 text-center">
                <Plus size={32} className="text-primary mx-auto mb-2" />
                <p className="text-primary font-medium text-sm">Suelta aqui para agregar</p>
              </div>
            </div>
          )}

          {widgets.length === 0 && !dragOverCanvas ? (
            <div className="border-2 border-dashed border-[#D1D5DB] rounded-xl min-h-[400px] flex items-center justify-center bg-white/50 m-2">
              <div className="text-center">
                <GripVertical size={40} className="text-[#D1D5DB] mx-auto mb-2" />
                <p className="text-[#6B7280] text-sm">Agrega consultas desde el panel lateral</p>
                <p className="text-[#9CA3AF] text-xs mt-1">Arrastra desde el panel o usa el boton Agregar</p>
              </div>
            </div>
          ) : widgets.length > 0 && (
            <ResponsiveGridLayout
              layouts={{ lg: gridLayout }}
              breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
              cols={{ lg: 12, md: 10, sm: 6, xs: 4 }}
              rowHeight={80}
              isDraggable
              isResizable
              compactType="vertical"
              margin={[8, 8]}
              containerPadding={[8, 8]}
              onLayoutChange={handleLayoutChange}
              draggableCancel=".no-drag"
              style={{ minHeight: 400 }}
            >
              {widgets.map(w => (
                <div key={w.grid_i}>
                  <div className="bg-white rounded-lg h-full flex flex-col overflow-hidden"
                    style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    {/* Header */}
                    <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#F3F4F6] flex-shrink-0">
                      {editingTitle === w.grid_i ? (
                        <input
                          data-title-edit={w.grid_i}
                          className="no-drag text-[13px] font-semibold border-0 border-b border-primary outline-none flex-1 mr-2 bg-transparent text-[#1F2937]"
                          value={w.custom_title || w.title}
                          onChange={e => updateWidgetField(w.grid_i, 'custom_title', e.target.value)}
                          onBlur={() => setEditingTitle(null)}
                          onKeyDown={e => { if (e.key === 'Enter') setEditingTitle(null) }}
                          autoFocus
                        />
                      ) : (
                        <span
                          className="text-[13px] font-semibold text-[#1F2937] truncate flex-1 cursor-text"
                          onClick={() => startEditTitle(w.grid_i)}
                          title="Clic para editar titulo"
                        >
                          {w.custom_title || w.title}
                        </span>
                      )}
                      <div className="no-drag flex gap-0.5 flex-shrink-0 relative">
                        {/* PROMPT 2: Pencil button with both onMouseDown and onClick */}
                        <button
                          onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                          onClick={e => { e.stopPropagation(); startEditTitle(w.grid_i) }}
                          className="p-1 rounded hover:bg-gray-100 transition-colors" title="Editar titulo"
                        >
                          <Pencil size={10} className="text-[#9CA3AF]" />
                        </button>
                        {(w.data?.length > 0 || w.is_title_block || w.type === 'text_card' || w.type === 'kpi') && (
                          <button
                            onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                            onClick={e => { e.stopPropagation(); setSettingsOpen(settingsOpen === w.grid_i ? null : w.grid_i) }}
                            className="p-1 rounded hover:bg-gray-100 transition-colors" title="Configuracion"
                          >
                            <Palette size={10} className="text-[#9CA3AF]" />
                          </button>
                        )}
                        {w.sql && (
                          <button
                            onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                            onClick={e => { e.stopPropagation(); setSqlModal({ title: w.title, sql: w.sql || '', queryText: w.query_text || '' }) }}
                            className="p-1 rounded hover:bg-gray-100 transition-colors" title="Ver SQL"
                          >
                            <Info size={10} className="text-[#9CA3AF]" />
                          </button>
                        )}
                        <button
                          onMouseDown={e => { e.stopPropagation(); e.preventDefault() }}
                          onClick={e => { e.stopPropagation(); removeWidget(w.grid_i) }}
                          className="p-1 rounded hover:bg-red-50 transition-colors" title="Eliminar"
                        >
                          <X size={10} className="text-[#9CA3AF] hover:text-red-500" />
                        </button>
                        {/* Settings dropdown */}
                        {settingsOpen === w.grid_i && (
                          <div className="no-drag absolute top-7 right-0 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-30 p-2 min-w-[180px]"
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => e.stopPropagation()}>
                            {/* Font size for title/text */}
                            {(w.is_title_block || w.type === 'text_card') && (
                              <>
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Tamano de texto</p>
                                <div className="flex flex-wrap gap-1 mb-1.5">
                                  {TEXT_SIZE_OPTIONS.map(opt => (
                                    <button
                                      key={opt.value}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'text_size', opt.value) }}
                                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                                        (w.text_size || (w.is_title_block ? 'lg' : 'sm')) === opt.value
                                          ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'
                                      }`}
                                    >
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                              </>
                            )}
                            {/* PROMPT 3: KPI style selector */}
                            {w.type === 'kpi' && (
                              <>
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Estilo de tarjeta</p>
                                <div className="flex flex-wrap gap-1 mb-1.5">
                                  {KPI_STYLE_OPTIONS.map(opt => (
                                    <button
                                      key={opt.value}
                                      onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'kpi_style', opt.value) }}
                                      className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                                        ((w as any).kpi_style || 'accent') === opt.value
                                          ? 'bg-primary text-white' : 'bg-[#F3F4F6] hover:bg-gray-200'
                                      }`}
                                    >
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                                {(w as any).kpi_style === 'progress' && (
                                  <input
                                    className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-1 outline-none focus:border-primary"
                                    placeholder="Valor maximo (ej: 1000)"
                                    type="number"
                                    value={(w as any).kpi_max_value || ''}
                                    onClick={e => e.stopPropagation()}
                                    onChange={e => updateWidgetField(w.grid_i, 'kpi_max_value', parseFloat(e.target.value) || undefined)}
                                  />
                                )}
                              </>
                            )}
                            {/* Color palette for chart widgets */}
                            {!w.is_title_block && w.type !== 'text_card' && (
                              <>
                                <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Paleta</p>
                                {Object.entries(COLOR_PALETTES).map(([key, pal]) => (
                                  <button
                                    key={key}
                                    onClick={e => { e.stopPropagation(); updateWidgetField(w.grid_i, 'color_palette', key) }}
                                    className={`w-full flex items-center gap-2 px-2 py-1 rounded text-[11px] hover:bg-[#F3F4F6] transition-colors ${w.color_palette === key ? 'bg-primary/10 font-semibold' : ''}`}
                                  >
                                    <div className="flex gap-0.5">
                                      {pal.colors.slice(0, 4).map((c, i) => (
                                        <div key={i} className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />
                                      ))}
                                    </div>
                                    <span>{pal.name}</span>
                                  </button>
                                ))}
                                {w.type !== 'kpi' && (
                                  <div className="border-t border-[#E5E7EB] mt-1.5 pt-1.5">
                                    <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wider px-1 mb-1">Ejes</p>
                                    <input
                                      className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded mb-1 outline-none focus:border-primary"
                                      placeholder="Etiqueta eje X"
                                      value={w.custom_x_label || ''}
                                      onClick={e => e.stopPropagation()}
                                      onChange={e => updateWidgetField(w.grid_i, 'custom_x_label', e.target.value)}
                                    />
                                    <input
                                      className="no-drag w-full text-[11px] px-2 py-1 border border-[#E5E7EB] rounded outline-none focus:border-primary"
                                      placeholder="Etiqueta eje Y"
                                      value={w.custom_y_label || ''}
                                      onClick={e => e.stopPropagation()}
                                      onChange={e => updateWidgetField(w.grid_i, 'custom_y_label', e.target.value)}
                                    />
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
                      {w.is_title_block ? (
                        <div className="no-drag flex items-center justify-center flex-1 px-4">
                          <input
                            className={`${TEXT_SIZE_CLASS[w.text_size || 'lg']} font-bold text-center w-full bg-transparent border-0 outline-none text-[#1F2937]`}
                            value={w.text_content || ''}
                            onChange={e => updateWidgetField(w.grid_i, 'text_content', e.target.value)}
                            placeholder="Titulo de seccion..."
                          />
                        </div>
                      ) : w.type === 'text_card' ? (
                        <div className="no-drag flex-1 flex flex-col gap-1 p-2">
                          <textarea
                            className={`flex-1 ${TEXT_SIZE_CLASS[w.text_size || 'sm']} bg-transparent border-0 outline-none resize-none text-[#374151]`}
                            value={w.text_content || ''}
                            onChange={e => updateWidgetField(w.grid_i, 'text_content', e.target.value)}
                            placeholder="Texto informativo..."
                          />
                          <input
                            className="text-xs text-primary bg-transparent border-0 border-b border-[#E5E7EB] outline-none"
                            value={w.text_url || ''}
                            onChange={e => updateWidgetField(w.grid_i, 'text_url', e.target.value)}
                            placeholder="URL (opcional)"
                          />
                        </div>
                      ) : w.type === 'kpi' && w.kpi_value !== undefined ? (
                        <div className="flex-1 flex items-center justify-center">
                          <KpiCard
                            label={w.kpi_label || w.title}
                            value={w.kpi_value}
                            color={PRIMARY_COLOR}
                            delta={w.kpi_delta}
                            kpiStyle={(w as any).kpi_style || 'accent'}
                            maxValue={(w as any).kpi_max_value}
                          />
                        </div>
                      ) : w.data?.length && w.columns?.length >= 2 ? (
                        <div className="flex-1 p-1" style={{ width: '100%', height: '100%' }}>
                          <ChartWidget
                            data={w.data}
                            columns={w.columns}
                            chartType={(w.chart_type || w.type || 'bar') as ChartType}
                            height={Math.max(w.grid_h * 80 - 48, 120)}
                            colors={w.color_palette ? COLOR_PALETTES[w.color_palette]?.colors : undefined}
                            xLabel={w.custom_x_label}
                            yLabel={w.custom_y_label}
                            showLegend={w.show_legend !== false}
                          />
                        </div>
                      ) : w.data?.length ? (
                        <div className="flex-1 text-xs overflow-auto p-2">
                          <table className="w-full">
                            <thead>
                              <tr className="bg-[#F9FAFB]">
                                {w.columns.map(c => (
                                  <th key={c} className="px-2 py-1 text-left text-[10px] font-semibold text-[#6B7280]">{c}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {w.data.slice(0, 8).map((row, ri) => (
                                <tr key={ri} className="border-b border-[#F3F4F6]">
                                  {w.columns.map(c => (
                                    <td key={c} className="px-2 py-1 text-[10px] truncate max-w-[120px]">{String(row[c] ?? '')}</td>
                                  ))}
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
              ))}
            </ResponsiveGridLayout>
          )}
        </div>
      </div>

      {/* ─── AI FAB — rendered via portal ─── */}
      {createPortal(
        <>
          <button
            onClick={() => setAiOpen(!aiOpen)}
            className="btn-primary rounded-full py-2.5 px-5 shadow-lg flex items-center gap-2"
            style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999 }}
          >
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
                  Describe que metricas quieres. Ejecutare la consulta y la agregare al canvas.
                  <br /><br />
                  Ejemplos:<br />
                  - "Agrega un KPI con el total de mensajes"<br />
                  - "Tendencia de mensajes por dia"<br />
                  - "Top 5 agentes por rendimiento"
                </div>
                {aiMessages.map((m, i) => (
                  <div key={i} className={`p-2 rounded-lg text-xs ${
                    m.role === 'user' ? 'bg-primary text-white ml-8' :
                    m.role === 'system' && m.content.startsWith('Agregado') ? 'bg-green-50 text-green-700' :
                    m.role === 'system' && m.content.startsWith('Error') ? 'bg-red-50 text-red-700' :
                    'bg-[#F3F4F6] text-[#374151]'
                  }`}>
                    {m.content}
                  </div>
                ))}
                {aiLoading && (
                  <div className="flex items-center gap-2 text-xs text-[#9CA3AF]">
                    <Loader2 size={12} className="animate-spin" /> Ejecutando y agregando...
                  </div>
                )}
              </div>
              <div className="p-4 border-t border-[#E5E7EB]">
                <div className="flex gap-2">
                  <input
                    className="flex-1 text-sm px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none focus:border-primary"
                    placeholder="Ej: Agrega una tarjeta con total de mensajes"
                    value={aiInput}
                    onChange={e => setAiInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAiSend()}
                  />
                  <button onClick={handleAiSend} className="btn-primary p-2 rounded-lg" disabled={aiLoading}>
                    <Send size={14} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </>,
        document.body
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
              {sqlModal.queryText && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">Pregunta original</p>
                  <p className="text-sm text-[#374151]">{sqlModal.queryText}</p>
                </div>
              )}
              {sqlModal.sql && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">SQL generado</p>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-lg text-xs overflow-x-auto font-mono whitespace-pre-wrap">{sqlModal.sql}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
