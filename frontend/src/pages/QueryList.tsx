import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Search, Star, Archive, BarChart3, MessageSquare,
  Clock, ArrowRight, Loader2,
} from 'lucide-react'
import { listQueries, toggleQueryFavorite, archiveQuery } from '../api/client'
import type { SavedQuery } from '../types'

export default function QueryList() {
  const [queries, setQueries] = useState<SavedQuery[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [favOnly, setFavOnly] = useState(false)
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const result = await listQueries({
        limit: 50,
        search: search || undefined,
        favorites_only: favOnly,
      })
      setQueries(result.queries)
      setTotal(result.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search, favOnly]) // eslint-disable-line

  const handleFavorite = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    await toggleQueryFavorite(id)
    load()
  }

  const handleArchive = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    await archiveQuery(id)
    load()
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">Consultas</h1>
          <p className="text-sm text-text-muted">{total} consultas guardadas</p>
        </div>
        <Link to="/consultas/nueva" className="btn-primary flex items-center gap-1.5 text-sm no-underline">
          <MessageSquare size={16} />
          Nueva Consulta
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
          <input
            className="input pl-9"
            placeholder="Buscar consultas..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button
          onClick={() => setFavOnly(!favOnly)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-btn text-sm transition-colors ${
            favOnly ? 'bg-yellow-50 text-yellow-600 border border-yellow-200' : 'btn-secondary'
          }`}
        >
          <Star size={14} fill={favOnly ? 'currentColor' : 'none'} />
          Favoritos
        </button>
      </div>

      {/* Query list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : queries.length === 0 ? (
        <div className="text-center py-16">
          <Search size={48} className="text-text-light mx-auto mb-3" />
          <p className="text-text-muted">No hay consultas guardadas</p>
          <Link to="/consultas/nueva" className="btn-primary mt-4 inline-flex items-center gap-1.5 text-sm no-underline">
            <MessageSquare size={14} /> Crear primera consulta
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {queries.map(q => {
            const chartType = q.visualizations?.[0]?.type || 'table'
            const hasConv = !!q.conversation_history?.length
            return (
              <div
                key={q.id}
                onClick={() => navigate(`/consultas/nueva?rerun=${q.id}`)}
                className="card px-4 py-3 flex items-center gap-4 cursor-pointer hover:shadow-card-hover transition-shadow"
              >
                {/* Icon */}
                <div className="w-9 h-9 rounded-btn bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <BarChart3 size={16} className="text-primary" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-text-dark truncate">{q.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="badge badge-primary">{chartType.toUpperCase()}</span>
                    <span className="text-[11px] text-text-muted">{q.result_row_count} filas</span>
                    {hasConv && (
                      <span className="badge badge-success text-[10px]">Chat</span>
                    )}
                    {q.ai_function && (
                      <span className="text-[11px] text-text-light">{q.ai_function}</span>
                    )}
                  </div>
                </div>

                {/* Time */}
                <div className="flex items-center gap-1 text-[11px] text-text-light flex-shrink-0">
                  <Clock size={11} />
                  {q.updated_at ? new Date(q.updated_at).toLocaleDateString('es-CO') : ''}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={e => handleFavorite(e, q.id)}
                    className="btn-icon p-1"
                    title="Favorito"
                  >
                    <Star size={14} fill={q.is_favorite ? '#FFC107' : 'none'} className={q.is_favorite ? 'text-yellow-500' : ''} />
                  </button>
                  <button
                    onClick={e => handleArchive(e, q.id)}
                    className="btn-icon p-1"
                    title="Archivar"
                  >
                    <Archive size={14} />
                  </button>
                  <ArrowRight size={14} className="text-text-light" />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
