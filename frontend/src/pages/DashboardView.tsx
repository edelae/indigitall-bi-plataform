import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Pencil, Loader2, ArrowLeft, Info, X, ExternalLink } from 'lucide-react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import ChartWidget from '../components/ChartWidget'
import KpiCard from '../components/KpiCard'
import type { Dashboard, DashboardWidget, ChartType } from '../types'
import { PRIMARY_COLOR, COLOR_PALETTES } from '../types'
import { getDashboard } from '../api/client'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

interface DashboardTab {
  id: string
  name: string
  widgets: DashboardWidget[]
}

export default function DashboardView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [infoModal, setInfoModal] = useState<DashboardWidget | null>(null)
  const [tabs, setTabs] = useState<DashboardTab[]>([])
  const [activeTabId, setActiveTabId] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getDashboard(parseInt(id))
      .then(d => {
        setDashboard(d)
        // Reconstruct tabs
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
      .catch(() => setDashboard(null))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="text-center py-24">
        <p className="text-[#6B7280] mb-4">Tablero no encontrado</p>
        <Link to="/tableros" className="btn-primary text-sm no-underline">Volver a tableros</Link>
      </div>
    )
  }

  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0]
  const widgets = activeTab?.widgets || []

  const gridLayout = widgets.map(w => ({
    i: w.grid_i,
    x: w.grid_x,
    y: w.grid_y,
    w: w.grid_w,
    h: w.grid_h,
    static: true,
  }))

  const handleChartClick = (widget: DashboardWidget) => {
    if (widget.query_id) {
      navigate(`/consultas/nueva?rerun=${widget.query_id}`)
    } else if (widget.query_text) {
      navigate(`/consultas/nueva?q=${encodeURIComponent(widget.query_text)}`)
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-[#1F2937]">{dashboard.name}</h1>
          {dashboard.description && <p className="text-sm text-[#6B7280] mt-0.5">{dashboard.description}</p>}
        </div>
        <div className="flex gap-2">
          <Link to={`/tableros/nuevo?edit=${dashboard.id}`} className="btn-secondary flex items-center gap-1.5 text-sm no-underline">
            <Pencil size={14} /> Editar
          </Link>
          <Link to="/tableros" className="btn-ghost flex items-center gap-1.5 text-sm no-underline">
            <ArrowLeft size={14} /> Tableros
          </Link>
        </div>
      </div>

      {/* Tabs bar */}
      {tabs.length > 1 && (
        <div className="flex items-center gap-0.5 mb-0 border-b border-[#E5E7EB] bg-white px-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${
                activeTabId === tab.id
                  ? 'border-primary text-primary bg-primary/5'
                  : 'border-transparent text-[#6B7280] hover:text-[#374151] hover:bg-gray-50'
              }`}
            >
              {tab.name}
            </button>
          ))}
        </div>
      )}

      {/* Canvas */}
      <div className="bg-[#F3F4F6] rounded-b-lg p-3 min-h-[400px]">
        {widgets.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-[#6B7280] mb-4">Este tablero no tiene widgets</p>
            <Link to={`/tableros/nuevo?edit=${dashboard.id}`} className="btn-primary text-sm no-underline inline-flex items-center gap-1.5">
              <Pencil size={14} /> Editar tablero
            </Link>
          </div>
        ) : (
          <ResponsiveGridLayout
            layouts={{ lg: gridLayout }}
            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
            cols={{ lg: 12, md: 10, sm: 6, xs: 4 }}
            rowHeight={80}
            isDraggable={false}
            isResizable={false}
            compactType="vertical"
            margin={[8, 8]}
            style={{ minHeight: 300 }}
          >
            {widgets.map(w => (
              <div key={w.grid_i}>
                <div className="bg-white rounded-lg h-full flex flex-col overflow-hidden"
                  style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                  {/* Title block — no header */}
                  {w.is_title_block ? (
                    <div className="flex items-center justify-center h-full px-4">
                      <h2 className="text-lg font-bold text-[#1F2937] text-center">{w.text_content || w.title}</h2>
                    </div>
                  ) : w.type === 'text_card' ? (
                    <div className="flex flex-col h-full p-4">
                      <p className="text-sm text-[#374151] flex-1">{w.text_content}</p>
                      {w.text_url && (
                        <a href={w.text_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary mt-2 underline">
                          {w.text_url}
                        </a>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#F3F4F6] flex-shrink-0">
                        <span className="text-[13px] font-semibold text-[#1F2937] truncate">{w.custom_title || w.title}</span>
                        <button onClick={() => setInfoModal(w)} className="p-0.5 hover:bg-gray-100 rounded" title="Ver info">
                          <Info size={10} className="text-[#9CA3AF]" />
                        </button>
                      </div>
                      <div
                        className="flex-1 overflow-hidden cursor-pointer flex flex-col"
                        onClick={() => handleChartClick(w)}
                        title="Clic para ir a la consulta"
                        style={{ minHeight: 0 }}
                      >
                        {w.type === 'kpi' && w.kpi_value !== undefined ? (
                          <div className="flex-1 flex items-center p-2">
                            <KpiCard label={w.kpi_label || w.title} value={w.kpi_value} color={PRIMARY_COLOR} />
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
                                {w.data.slice(0, 10).map((row, ri) => (
                                  <tr key={ri} className="border-b border-[#F3F4F6]">
                                    {w.columns.map(c => (
                                      <td key={c} className="px-2 py-1 text-[10px] truncate max-w-[150px]">{String(row[c] ?? '')}</td>
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
                    </>
                  )}
                </div>
              </div>
            ))}
          </ResponsiveGridLayout>
        )}
      </div>

      {/* Info Modal */}
      {infoModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setInfoModal(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
              <h3 className="font-semibold text-[#1F2937]">{infoModal.custom_title || infoModal.title}</h3>
              <button onClick={() => setInfoModal(null)} className="p-1 hover:bg-gray-100 rounded"><X size={16} /></button>
            </div>
            <div className="p-4 space-y-3">
              {infoModal.query_text && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">Pregunta original</p>
                  <p className="text-sm text-[#374151]">{infoModal.query_text}</p>
                </div>
              )}
              <div className="flex gap-2">
                <span className="text-[9px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">
                  {(infoModal.chart_type || infoModal.type || 'table').toUpperCase()}
                </span>
                <span className="text-[9px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded font-medium">
                  {infoModal.data?.length || 0} filas
                </span>
              </div>
              {infoModal.sql && (
                <div>
                  <p className="text-xs font-semibold text-[#6B7280] mb-1">SQL</p>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-lg text-xs overflow-x-auto font-mono whitespace-pre-wrap">{infoModal.sql}</pre>
                </div>
              )}
              {(infoModal.query_id || infoModal.query_text) && (
                <Link
                  to={infoModal.query_id ? `/consultas/nueva?rerun=${infoModal.query_id}` : `/consultas/nueva?q=${encodeURIComponent(infoModal.query_text || '')}`}
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
