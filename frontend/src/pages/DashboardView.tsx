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

export default function DashboardView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [infoModal, setInfoModal] = useState<DashboardWidget | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getDashboard(parseInt(id))
      .then(setDashboard)
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
        <p className="text-text-muted mb-4">Tablero no encontrado</p>
        <Link to="/tableros" className="btn-primary text-sm no-underline">Volver a tableros</Link>
      </div>
    )
  }

  const widgets = (dashboard.layout || []).map((w, i) => ({
    ...w,
    grid_i: w.grid_i || `widget-${i}`,
    grid_x: w.grid_x ?? (i % 2) * 6,
    grid_y: w.grid_y ?? Math.floor(i / 2) * 4,
    grid_w: w.grid_w ?? w.width ?? 6,
    grid_h: w.grid_h ?? 4,
  }))

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
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">{dashboard.name}</h1>
          {dashboard.description && <p className="text-sm text-text-muted mt-1">{dashboard.description}</p>}
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

      {widgets.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-text-muted mb-4">Este tablero no tiene widgets</p>
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
          margin={[12, 12]}
          style={{ minHeight: 300 }}
        >
          {widgets.map(w => (
            <div key={w.grid_i}>
              <div className="card h-full flex flex-col overflow-hidden">
                {/* Title block — no header */}
                {w.is_title_block ? (
                  <div className="flex items-center justify-center h-full px-4">
                    <h2 className="text-lg font-bold text-text-dark text-center">{w.text_content || w.title}</h2>
                  </div>
                ) : w.type === 'text_card' ? (
                  <div className="flex flex-col h-full p-4">
                    <p className="text-sm text-text-dark flex-1">{w.text_content}</p>
                    {w.text_url && (
                      <a href={w.text_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary mt-2 underline">
                        {w.text_url}
                      </a>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between px-3 py-1.5 bg-white border-b border-border-light">
                      <span className="text-xs font-semibold text-text-dark truncate">{w.custom_title || w.title}</span>
                      <button onClick={() => setInfoModal(w)} className="btn-icon p-0.5" title="Ver info">
                        <Info size={11} />
                      </button>
                    </div>
                    <div
                      className="flex-1 p-2 overflow-hidden cursor-pointer"
                      onClick={() => handleChartClick(w)}
                      title="Clic para ir a la consulta"
                    >
                      {w.type === 'kpi' && w.kpi_value !== undefined ? (
                        <KpiCard label={w.kpi_label || w.title} value={w.kpi_value} color={PRIMARY_COLOR} />
                      ) : w.data?.length && w.columns?.length >= 2 ? (
                        <ChartWidget
                          data={w.data}
                          columns={w.columns}
                          chartType={(w.chart_type || w.type || 'bar') as ChartType}
                          height={Math.max(w.grid_h * 80 - 60, 140)}
                          colors={w.color_palette ? COLOR_PALETTES[w.color_palette]?.colors : undefined}
                          xLabel={w.custom_x_label}
                          yLabel={w.custom_y_label}
                          showLegend={w.show_legend !== false}
                        />
                      ) : w.data?.length ? (
                        <div className="text-xs overflow-auto h-full">
                          <table className="w-full">
                            <thead>
                              <tr className="bg-surface">
                                {w.columns.map(c => (
                                  <th key={c} className="px-2 py-1 text-left text-[10px] font-semibold text-text-muted">{c}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {w.data.slice(0, 10).map((row, ri) => (
                                <tr key={ri} className="border-b border-border-light">
                                  {w.columns.map(c => (
                                    <td key={c} className="px-2 py-1 text-[10px] truncate max-w-[150px]">{String(row[c] ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center h-full text-xs text-text-muted">Sin datos</div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </ResponsiveGridLayout>
      )}

      {/* Info Modal */}
      {infoModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setInfoModal(null)}>
          <div className="bg-white rounded-card shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-border-light">
              <h3 className="font-semibold">{infoModal.custom_title || infoModal.title}</h3>
              <button onClick={() => setInfoModal(null)} className="btn-icon"><X size={16} /></button>
            </div>
            <div className="p-4 space-y-3">
              {infoModal.query_text && (
                <div>
                  <p className="text-xs font-semibold text-text-muted mb-1">Pregunta original</p>
                  <p className="text-sm">{infoModal.query_text}</p>
                </div>
              )}
              <div className="flex gap-2">
                <span className="badge badge-primary">{(infoModal.chart_type || infoModal.type || 'table').toUpperCase()}</span>
                <span className="badge badge-info">{infoModal.data?.length || 0} filas</span>
              </div>
              {infoModal.sql && (
                <div>
                  <p className="text-xs font-semibold text-text-muted mb-1">SQL</p>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-btn text-xs overflow-x-auto font-mono whitespace-pre-wrap">{infoModal.sql}</pre>
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
