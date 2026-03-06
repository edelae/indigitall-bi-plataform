import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Search, Star, Archive, BarChart3, MessageSquare,
  Clock, ArrowRight, Loader2, FolderPlus, Folder,
  ChevronDown, ChevronRight,
} from 'lucide-react'
import { listQueries, toggleQueryFavorite, archiveQuery } from '../api/client'
import type { SavedQuery, QueryFolder } from '../types'

const STORAGE_KEY = 'indigitall_query_folders'
const FOLDER_MAP_KEY = 'indigitall_query_folder_map'

function loadFolders(): QueryFolder[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch { return [] }
}

function saveFolders(folders: QueryFolder[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(folders))
}

function loadFolderMap(): Record<number, string> {
  try {
    return JSON.parse(localStorage.getItem(FOLDER_MAP_KEY) || '{}')
  } catch { return {} }
}

function saveFolderMap(map: Record<number, string>) {
  localStorage.setItem(FOLDER_MAP_KEY, JSON.stringify(map))
}

export default function QueryList() {
  const [queries, setQueries] = useState<SavedQuery[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [favOnly, setFavOnly] = useState(false)
  const navigate = useNavigate()

  // Folders
  const [folders, setFolders] = useState<QueryFolder[]>(loadFolders)
  const [folderMap, setFolderMap] = useState<Record<number, string>>(loadFolderMap)
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [newFolderName, setNewFolderName] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [contextMenu, setContextMenu] = useState<{ queryId: number; x: number; y: number } | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const result = await listQueries({ limit: 100, search: search || undefined, favorites_only: favOnly })
      setQueries(result.queries)
      setTotal(result.total)
    } catch { /* ignore */ } finally {
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

  const createFolder = () => {
    if (!newFolderName.trim()) return
    const newFolder: QueryFolder = {
      id: `folder-${Date.now()}`,
      name: newFolderName.trim(),
    }
    const updated = [...folders, newFolder]
    setFolders(updated)
    saveFolders(updated)
    setNewFolderName('')
    setShowNewFolder(false)
    setExpandedFolders(prev => new Set([...prev, newFolder.id]))
  }

  const assignToFolder = (queryId: number, folderId: string | null) => {
    const updated = { ...folderMap }
    if (folderId) {
      updated[queryId] = folderId
    } else {
      delete updated[queryId]
    }
    setFolderMap(updated)
    saveFolderMap(updated)
    setContextMenu(null)
  }

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(folderId)) next.delete(folderId)
      else next.add(folderId)
      return next
    })
  }

  const handleContextMenu = (e: React.MouseEvent, queryId: number) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ queryId, x: e.clientX, y: e.clientY })
  }

  // Group queries by folder
  const queriesByFolder = new Map<string | null, SavedQuery[]>()
  for (const folder of folders) {
    queriesByFolder.set(folder.id, [])
  }
  queriesByFolder.set(null, [])

  for (const q of queries) {
    const folderId = folderMap[q.id] || null
    if (folderId && queriesByFolder.has(folderId)) {
      queriesByFolder.get(folderId)!.push(q)
    } else {
      queriesByFolder.get(null)!.push(q)
    }
  }

  const renderQuery = (q: SavedQuery) => {
    const chartType = q.visualizations?.[0]?.type || 'table'
    const hasConv = !!q.conversation_history?.length
    return (
      <div
        key={q.id}
        onClick={() => navigate(`/consultas/nueva?rerun=${q.id}`)}
        onContextMenu={e => handleContextMenu(e, q.id)}
        className="card px-4 py-3 flex items-center gap-4 cursor-pointer hover:shadow-card-hover transition-shadow"
      >
        <div className="w-9 h-9 rounded-btn bg-primary/10 flex items-center justify-center flex-shrink-0">
          <BarChart3 size={16} className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text-dark truncate">{q.name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="badge badge-primary">{chartType.toUpperCase()}</span>
            <span className="text-[11px] text-text-muted">{q.result_row_count} filas</span>
            {hasConv && <span className="badge badge-success text-[10px]">Chat</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-text-light flex-shrink-0">
          <Clock size={11} />
          {q.updated_at ? new Date(q.updated_at).toLocaleDateString('es-CO') : ''}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={e => handleFavorite(e, q.id)} className="btn-icon p-1" title="Favorito">
            <Star size={14} fill={q.is_favorite ? '#FFC107' : 'none'} className={q.is_favorite ? 'text-yellow-500' : ''} />
          </button>
          <button onClick={e => handleArchive(e, q.id)} className="btn-icon p-1" title="Archivar">
            <Archive size={14} />
          </button>
          <ArrowRight size={14} className="text-text-light" />
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in" onClick={() => setContextMenu(null)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">Consultas</h1>
          <p className="text-sm text-text-muted">{total} consultas guardadas</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowNewFolder(true)} className="btn-secondary flex items-center gap-1.5 text-sm">
            <FolderPlus size={14} /> Nueva Carpeta
          </button>
          <Link to="/consultas/nueva" className="btn-primary flex items-center gap-1.5 text-sm no-underline">
            <MessageSquare size={16} /> Nueva Consulta
          </Link>
        </div>
      </div>

      {/* New folder input */}
      {showNewFolder && (
        <div className="mb-4 flex gap-2 items-center">
          <Folder size={16} className="text-primary" />
          <input
            className="input max-w-xs"
            placeholder="Nombre de la carpeta..."
            value={newFolderName}
            onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createFolder()}
            autoFocus
          />
          <button onClick={createFolder} className="btn-primary text-sm">Crear</button>
          <button onClick={() => setShowNewFolder(false)} className="btn-ghost text-sm">Cancelar</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
          <input className="input pl-9" placeholder="Buscar consultas..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <button
          onClick={() => setFavOnly(!favOnly)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-btn text-sm transition-colors ${
            favOnly ? 'bg-yellow-50 text-yellow-600 border border-yellow-200' : 'btn-secondary'
          }`}
        >
          <Star size={14} fill={favOnly ? 'currentColor' : 'none'} /> Favoritos
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
        <div className="space-y-1">
          {/* Folders */}
          {folders.map(folder => {
            const folderQueries = queriesByFolder.get(folder.id) || []
            const isExpanded = expandedFolders.has(folder.id)
            return (
              <div key={folder.id}>
                <button
                  onClick={() => toggleFolder(folder.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-btn text-sm font-semibold text-text-dark hover:bg-surface transition-colors"
                >
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <Folder size={14} className="text-primary" />
                  {folder.name}
                  <span className="badge badge-info text-[10px] ml-1">{folderQueries.length}</span>
                </button>
                {isExpanded && (
                  <div className="ml-6 space-y-1 mb-2">
                    {folderQueries.length === 0 ? (
                      <p className="text-xs text-text-light px-3 py-2">Carpeta vacia — clic derecho en una consulta para moverla aqui</p>
                    ) : (
                      folderQueries.map(renderQuery)
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {/* Unfiled queries */}
          {(queriesByFolder.get(null) || []).length > 0 && folders.length > 0 && (
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider px-3 pt-3 pb-1">
              Sin carpeta
            </p>
          )}
          <div className="space-y-1">
            {(queriesByFolder.get(null) || []).map(renderQuery)}
          </div>
        </div>
      )}

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed bg-white rounded-btn shadow-card-hover border border-border-light z-50 py-1 min-w-[180px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={e => e.stopPropagation()}
        >
          <p className="text-[10px] text-text-light uppercase tracking-wider px-3 py-1">Mover a carpeta</p>
          {folders.map(f => (
            <button
              key={f.id}
              onClick={() => assignToFolder(contextMenu.queryId, f.id)}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-surface flex items-center gap-2"
            >
              <Folder size={12} className="text-primary" /> {f.name}
            </button>
          ))}
          {folderMap[contextMenu.queryId] && (
            <button
              onClick={() => assignToFolder(contextMenu.queryId, null)}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-surface text-red-500"
            >
              Quitar de carpeta
            </button>
          )}
          {folders.length === 0 && (
            <p className="text-xs text-text-light px-3 py-2">Crea una carpeta primero</p>
          )}
        </div>
      )}
    </div>
  )
}
