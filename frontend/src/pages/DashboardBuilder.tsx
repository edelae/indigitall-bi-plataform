import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import {
  Save, ArrowLeft, Plus, X, Info, Loader2,
  Sparkles, Send, Play, GripVertical,
} from 'lucide-react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import type { DashboardWidget, SavedQuery, ChartType } from '../types'
import {
  listQueries, getQuery, getDashboard,
  saveDashboard, updateDashboard, sendChat,
} from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

export default function DashboardBuilder() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [widgets, setWidgets] = useState<DashboardWidget[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [dashboardId, setDashboardId] = useState<number | null>(null)
  const [queries, setQueries] = useState<SavedQuery[]>([])
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // AI Assistant
  const [aiOpen, setAiOpen] = useState(false)
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiMessages, setAiMessages] = useState<{ role: string; content: string }[]>([])

  // SQL Modal
  const [sqlModal, setSqlModal] = useState<{ title: string; sql: string; queryText: string } | null>(null)

  // Load available queries
  useEffect(() => {
    listQueries({ limit: 30 }).then(r => setQueries(r.queries)).catch(() => {})
  }, [])

  // Load existing dashboard or preload query
  useEffect(() => {
    const editId = searchParams.get('edit')
    const queryId = searchParams.get('query_id')

    if (editId) {
      getDashboard(parseInt(editId)).then(d => {
        setName(d.name)
        setDescription(d.description || '')
        setDashboardId(d.id)
        const loaded = (d.layout || []).map((w: DashboardWidget, i: number) => ({
          ...w,
          grid_i: w.grid_i || `widget-${i}`,
          grid_x: w.grid_x ?? (i % 2) * 6,
          grid_y: w.grid_y ?? Math.floor(i / 2) * 4,
          grid_w: w.grid_w ?? w.width ?? 6,
          grid_h: w.grid_h ?? 4,
        }))
        setWidgets(loaded)
      }).catch(() => {})
    } else if (queryId) {
      addQueryWidget(parseInt(queryId))
    }
  }, []) // eslint-disable-line

  const addQueryWidget = async (queryId: number) => {
    try {
      const q = await getQuery(queryId)
      const chartType = q.visualizations?.[0]?.type || 'bar'
      const idx = widgets.length
      const newWidget: DashboardWidget = {
        query_id: q.id,
        title: q.name.slice(0, 60),
        type: chartType,
        chart_type: chartType,
        width: 6,
        data: q.result_data || [],
        columns: (q.result_columns || []).map(c => c.name),
        sql: q.generated_sql || '',
        query_text: q.query_text || '',
        grid_i: `widget-${idx}`,
        grid_x: (idx % 2) * 6,
        grid_y: Math.floor(idx / 2) * 4,
        grid_w: 6,
        grid_h: 4,
      }
      setWidgets(prev => [...prev, newWidget])
    } catch {
      // ignore
    }
  }

  const removeWidget = (index: number) => {
    setWidgets(prev => prev.filter((_, i) => i !== index))
  }

  const handleLayoutChange = useCallback((layout: any[]) => {
    setWidgets(prev => {
      const updated = [...prev]
      for (const item of layout) {
        const idx = updated.findIndex(w => w.grid_i === item.i)
        if (idx >= 0) {
          updated[idx] = {
            ...updated[idx],
            grid_x: item.x,
            grid_y: item.y,
            grid_w: item.w,
            grid_h: item.h,
            width: item.w,
          }
        }
      }
      return updated
    })
  }, [])

  const handleSave = async () => {
    if (!name.trim()) {
      setFeedback({ type: 'error', text: 'Ingresa un nombre para el tablero' })
      return
    }
    if (!widgets.length) {
      setFeedback({ type: 'error', text: 'Agrega al menos un widget' })
      return
    }

    setSaving(true)
    try {
      if (dashboardId) {
        await updateDashboard(dashboardId, widgets)
        setFeedback({ type: 'success', text: 'Tablero actualizado' })
      } else {
        const result = await saveDashboard({ name: name.trim(), description: description.trim(), layout: widgets })
        setDashboardId(result.id)
        setFeedback({ type: 'success', text: 'Tablero guardado' })
      }
    } catch {
      setFeedback({ type: 'error', text: 'Error guardando el tablero' })
    } finally {
      setSaving(false)
      setTimeout(() => setFeedback(null), 4000)
    }
  }

  // AI: execute question and add as widget
  const executeAiQuestion = async (question: string) => {
    setAiLoading(true)
    try {
      const result = await sendChat(question)
      if (result.data?.length) {
        const idx = widgets.length
        const newWidget: DashboardWidget = {
          title: question.slice(0, 60),
          type: result.chart_type || 'bar',
          chart_type: result.chart_type || 'bar',
          width: 6,
          data: result.data,
          columns: result.columns,
          sql: result.query_details?.sql || '',
          query_text: question,
          grid_i: `widget-${idx}`,
          grid_x: (idx % 2) * 6,
          grid_y: 999,
          grid_w: 6,
          grid_h: 4,
        }
        setWidgets(prev => [...prev, newWidget])
        setAiMessages(prev => [...prev, { role: 'system', content: `Agregado: "${question}" (${result.data.length} filas)` }])
      } else {
        setAiMessages(prev => [...prev, { role: 'system', content: `Sin datos para: "${question}"` }])
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

  const gridLayout = widgets.map(w => ({
    i: w.grid_i,
    x: w.grid_x,
    y: w.grid_y,
    w: w.grid_w,
    h: w.grid_h,
    minW: 3,
    minH: 3,
  }))

  return (
    <div className="animate-fade-in">
      {/* Top bar */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 max-w-lg">
          <input
            className="w-full text-lg font-semibold border-0 border-b-2 border-border-light focus:border-primary outline-none pb-1 bg-transparent"
            placeholder="Nombre del tablero..."
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            className="w-full text-sm text-text-muted border-0 border-b border-border-light focus:border-primary/50 outline-none pb-1 mt-1 bg-transparent"
            placeholder="Descripcion (opcional)..."
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-1.5 text-sm">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {dashboardId ? 'Actualizar' : 'Guardar'}
          </button>
          <Link to="/tableros" className="btn-secondary flex items-center gap-1.5 text-sm no-underline">
            <ArrowLeft size={14} /> Volver
          </Link>
        </div>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`mb-4 px-4 py-2 rounded-btn text-sm ${
          feedback.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {feedback.text}
          {feedback.type === 'success' && dashboardId && (
            <Link to={`/tableros/saved/${dashboardId}`} className="ml-2 underline">Ver tablero</Link>
          )}
        </div>
      )}

      {/* Main: sidebar + canvas */}
      <div className="flex gap-4">
        {/* Sidebar: queries */}
        <div className="w-64 flex-shrink-0 border-r border-border-light pr-4 max-h-[calc(100vh-200px)] overflow-y-auto">
          <h3 className="text-sm font-semibold text-text-dark mb-3 flex items-center gap-1.5">
            <GripVertical size={14} />
            Consultas Guardadas
          </h3>
          {queries.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-xs text-text-muted">No hay consultas</p>
              <Link to="/consultas/nueva" className="text-xs text-primary">Crear consulta</Link>
            </div>
          ) : (
            queries.map(q => {
              const chartType = q.visualizations?.[0]?.type || 'table'
              return (
                <div key={q.id} className="card p-2.5 mb-2 hover:shadow-card-hover transition-shadow">
                  <p className="text-xs font-semibold text-text-dark truncate">{q.name}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="badge badge-primary text-[9px]">{chartType.toUpperCase()}</span>
                    <span className="text-[10px] text-text-muted">{q.result_row_count} filas</span>
                  </div>
                  <button
                    onClick={() => addQueryWidget(q.id)}
                    className="w-full mt-2 text-xs py-1 rounded-btn border border-primary/30 text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-1"
                  >
                    <Plus size={12} /> Agregar
                  </button>
                </div>
              )
            })
          )}
        </div>

        {/* Canvas */}
        <div className="flex-1 min-w-0">
          {widgets.length === 0 ? (
            <div className="border-2 border-dashed border-border rounded-card min-h-[400px] flex items-center justify-center">
              <div className="text-center">
                <GripVertical size={48} className="text-text-light mx-auto mb-3" />
                <p className="text-text-muted text-sm">Agrega consultas desde el panel lateral</p>
                <p className="text-text-light text-xs mt-1">Arrastra y redimensiona los widgets libremente</p>
              </div>
            </div>
          ) : (
            <ResponsiveGridLayout
              layouts={{ lg: gridLayout }}
              breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
              cols={{ lg: 12, md: 10, sm: 6, xs: 4 }}
              rowHeight={80}
              isDraggable
              isResizable
              compactType="vertical"
              margin={[16, 16]}
              onLayoutChange={handleLayoutChange}
              style={{ minHeight: 400 }}
            >
              {widgets.map((w, i) => (
                <div key={w.grid_i}>
                  <div className="card h-full flex flex-col overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-2 bg-white border-b border-border-light">
                      <span className="text-xs font-semibold text-text-dark truncate">{w.title}</span>
                      <div className="flex gap-0.5">
                        <button
                          onClick={() => setSqlModal({ title: w.title, sql: w.sql || '', queryText: w.query_text || '' })}
                          className="btn-icon p-0.5"
                          title="Ver SQL"
                        >
                          <Info size={12} />
                        </button>
                        <button
                          onClick={() => removeWidget(i)}
                          className="btn-icon p-0.5 hover:text-red-500"
                          title="Eliminar"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 p-2 overflow-hidden">
                      {w.data?.length && w.columns?.length >= 2 ? (
                        <ChartWidget
                          data={w.data}
                          columns={w.columns}
                          chartType={(w.type || 'bar') as ChartType}
                          height={Math.max(w.grid_h * 80 - 100, 150)}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full text-xs text-text-muted">
                          Sin datos
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </ResponsiveGridLayout>
          )}
        </div>
      </div>

      {/* AI FAB */}
      <button
        onClick={() => setAiOpen(!aiOpen)}
        className="fixed bottom-6 right-6 btn-primary rounded-pill py-2.5 px-5 shadow-lg flex items-center gap-2 z-40"
      >
        <Sparkles size={16} /> Asistente IA
      </button>

      {/* AI Slide-over */}
      {aiOpen && (
        <div className="fixed top-0 right-0 w-96 h-full bg-white shadow-2xl z-50 flex flex-col border-l border-border-light">
          <div className="flex items-center justify-between p-4 border-b border-border-light">
            <h3 className="font-semibold text-sm">Asistente IA para Tableros</h3>
            <button onClick={() => setAiOpen(false)} className="btn-icon"><X size={16} /></button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            <div className="bg-surface p-3 rounded-card text-xs text-text-muted">
              <Sparkles size={14} className="text-primary inline mr-1" />
              Describe que metricas quieres ver. Ejecutare las consultas y las agregare como widgets.
            </div>
            {aiMessages.map((m, i) => (
              <div key={i} className={`p-2 rounded-btn text-xs ${
                m.role === 'user' ? 'bg-primary text-white ml-8' :
                m.role === 'system' && m.content.startsWith('Agregado') ? 'bg-green-50 text-green-700' :
                m.role === 'system' && m.content.startsWith('Error') ? 'bg-red-50 text-red-700' :
                'bg-yellow-50 text-yellow-700'
              }`}>
                {m.content}
              </div>
            ))}
            {aiLoading && (
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Loader2 size={12} className="animate-spin" /> Ejecutando...
              </div>
            )}
          </div>

          <div className="p-4 border-t border-border-light">
            <div className="flex gap-2">
              <input
                className="input text-sm"
                placeholder="Ej: Tendencia de mensajes y top contactos"
                value={aiInput}
                onChange={e => setAiInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAiSend()}
              />
              <button onClick={handleAiSend} className="btn-primary p-2" disabled={aiLoading}>
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SQL Modal */}
      {sqlModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setSqlModal(null)}>
          <div className="bg-white rounded-card shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-border-light">
              <h3 className="font-semibold">{sqlModal.title}</h3>
              <button onClick={() => setSqlModal(null)} className="btn-icon"><X size={16} /></button>
            </div>
            <div className="p-4 space-y-3">
              {sqlModal.queryText && (
                <div>
                  <p className="text-xs font-semibold text-text-muted mb-1">Pregunta original</p>
                  <p className="text-sm">{sqlModal.queryText}</p>
                </div>
              )}
              {sqlModal.sql && (
                <div>
                  <p className="text-xs font-semibold text-text-muted mb-1">SQL generado</p>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-btn text-xs overflow-x-auto font-mono">
                    {sqlModal.sql}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
