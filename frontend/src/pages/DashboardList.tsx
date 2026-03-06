import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LayoutGrid, Plus, Search, Star, Archive,
  Clock, Loader2, Pencil, Eye, BarChart3, PieChart, LineChart,
} from 'lucide-react'
import { listDashboards, toggleDashboardFavorite, archiveDashboard } from '../api/client'
import type { Dashboard } from '../types'
import { CHART_COLORS } from '../types'

// Mini chart icon based on type
function MiniChart({ type, index }: { type: string; index: number }) {
  const color = CHART_COLORS[index % CHART_COLORS.length]
  if (type === 'pie' || type === 'kpi') return <PieChart size={16} style={{ color }} />
  if (type === 'line' || type === 'area') return <LineChart size={16} style={{ color }} />
  return <BarChart3 size={16} style={{ color }} />
}

export default function DashboardList() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const result = await listDashboards({ limit: 50, search: search || undefined })
      setDashboards(result.dashboards)
      setTotal(result.total)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search]) // eslint-disable-line

  const handleFavorite = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    await toggleDashboardFavorite(id)
    load()
  }

  const handleArchive = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (confirm('Archivar este tablero?')) {
      await archiveDashboard(id)
      load()
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">Tableros</h1>
          <p className="text-sm text-text-muted">{total} tableros creados</p>
        </div>
        <Link to="/tableros/nuevo" className="btn-primary flex items-center gap-1.5 text-sm no-underline">
          <Plus size={16} /> Nuevo Tablero
        </Link>
      </div>

      <div className="relative max-w-sm mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
        <input
          className="input pl-9"
          placeholder="Buscar tableros..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : dashboards.length === 0 ? (
        <div className="text-center py-16">
          <LayoutGrid size={48} className="text-text-light mx-auto mb-3" />
          <p className="text-text-muted">No hay tableros creados</p>
          <Link to="/tableros/nuevo" className="btn-primary mt-4 inline-flex items-center gap-1.5 text-sm no-underline">
            <Plus size={14} /> Crear tablero
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {dashboards.map(d => {
            const widgetCount = d.layout?.length || 0
            const isHovered = hoveredId === d.id
            return (
              <div
                key={d.id}
                onMouseEnter={() => setHoveredId(d.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="card overflow-hidden cursor-pointer hover:shadow-card-hover transition-all relative"
              >
                {/* Thumbnail area — mini preview of widget types */}
                <div className="bg-surface p-4 h-36 relative overflow-hidden">
                  {widgetCount > 0 ? (
                    <div className="grid grid-cols-3 gap-2 h-full">
                      {(d.layout || []).slice(0, 6).map((w, i) => (
                        <div key={i} className="bg-white rounded-btn shadow-sm flex items-center justify-center p-1">
                          <MiniChart type={w.type || w.chart_type || 'bar'} index={i} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <LayoutGrid size={32} className="text-text-light" />
                    </div>
                  )}

                  {/* Hover overlay with actions */}
                  {isHovered && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-3 animate-fade-in">
                      <button
                        onClick={() => navigate(`/tableros/saved/${d.id}`)}
                        className="bg-white text-text-dark px-4 py-2 rounded-btn text-sm font-medium flex items-center gap-1.5 hover:bg-gray-50 transition-colors"
                      >
                        <Eye size={14} /> Ver
                      </button>
                      <button
                        onClick={() => navigate(`/tableros/nuevo?edit=${d.id}`)}
                        className="bg-primary text-white px-4 py-2 rounded-btn text-sm font-medium flex items-center gap-1.5 hover:bg-primary-dark transition-colors"
                      >
                        <Pencil size={14} /> Editar
                      </button>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-semibold text-sm text-text-dark line-clamp-1">{d.name}</h3>
                    <div className="flex gap-1 flex-shrink-0 ml-2">
                      <button onClick={e => handleFavorite(e, d.id)} className="btn-icon p-0.5">
                        <Star size={13} fill={d.is_favorite ? '#FFC107' : 'none'} className={d.is_favorite ? 'text-yellow-500' : ''} />
                      </button>
                      <button onClick={e => handleArchive(e, d.id)} className="btn-icon p-0.5">
                        <Archive size={13} />
                      </button>
                    </div>
                  </div>
                  {d.description && (
                    <p className="text-xs text-text-muted line-clamp-2 mb-2">{d.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-[11px] text-text-light">
                    <span className="flex items-center gap-1">
                      <Clock size={11} />
                      {d.updated_at ? new Date(d.updated_at).toLocaleDateString('es-CO') : ''}
                    </span>
                    <span className="badge badge-info">{widgetCount} widgets</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
