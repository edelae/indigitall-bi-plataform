import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LayoutGrid, Plus, Search, Star, Archive,
  Clock, ArrowRight, Loader2,
} from 'lucide-react'
import { listDashboards, toggleDashboardFavorite, archiveDashboard } from '../api/client'
import type { Dashboard } from '../types'

export default function DashboardList() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const result = await listDashboards({ limit: 50, search: search || undefined })
      setDashboards(result.dashboards)
      setTotal(result.total)
    } catch {
      // ignore
    } finally {
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
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">Tableros</h1>
          <p className="text-sm text-text-muted">{total} tableros creados</p>
        </div>
        <Link to="/tableros/nuevo" className="btn-primary flex items-center gap-1.5 text-sm no-underline">
          <Plus size={16} /> Nuevo Tablero
        </Link>
      </div>

      {/* Search */}
      <div className="relative max-w-sm mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
        <input
          className="input pl-9"
          placeholder="Buscar tableros..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* List */}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map(d => (
            <div
              key={d.id}
              onClick={() => navigate(`/tableros/saved/${d.id}`)}
              className="card p-4 cursor-pointer hover:shadow-card-hover transition-shadow"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="w-10 h-10 bg-primary/10 rounded-btn flex items-center justify-center">
                  <LayoutGrid size={20} className="text-primary" />
                </div>
                <div className="flex gap-1">
                  <button onClick={e => handleFavorite(e, d.id)} className="btn-icon p-1">
                    <Star size={14} fill={d.is_favorite ? '#FFC107' : 'none'} className={d.is_favorite ? 'text-yellow-500' : ''} />
                  </button>
                  <button onClick={e => handleArchive(e, d.id)} className="btn-icon p-1">
                    <Archive size={14} />
                  </button>
                </div>
              </div>
              <h3 className="font-semibold text-sm text-text-dark mb-1">{d.name}</h3>
              {d.description && (
                <p className="text-xs text-text-muted line-clamp-2 mb-2">{d.description}</p>
              )}
              <div className="flex items-center gap-2 text-[11px] text-text-light mt-auto">
                <Clock size={11} />
                {d.updated_at ? new Date(d.updated_at).toLocaleDateString('es-CO') : ''}
                <span className="badge badge-info ml-auto">{d.layout?.length || 0} widgets</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
