import { useEffect, useState } from 'react'
import {
  Database, Table2, ChevronRight, Loader2,
  Hash, Type, Calendar, ToggleLeft, Search,
} from 'lucide-react'
import DataTable from '../components/DataTable'
import { listTables, previewTable } from '../api/client'
import type { TableInfo } from '../types'

const TYPE_ICONS: Record<string, typeof Hash> = {
  integer: Hash, bigint: Hash, numeric: Hash, 'double precision': Hash,
  'character varying': Type, text: Type,
  boolean: ToggleLeft,
  'timestamp with time zone': Calendar, 'timestamp without time zone': Calendar, date: Calendar,
  jsonb: Database, json: Database,
}

export default function DataExplorer() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTable, setSelectedTable] = useState<{ name: string; schema: string } | null>(null)
  const [previewData, setPreviewData] = useState<{ columns: string[]; data: Record<string, any>[]; total: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    listTables()
      .then(setTables)
      .catch(() => setTables([]))
      .finally(() => setLoading(false))
  }, [])

  const handleSelectTable = async (name: string, schema: string = 'public') => {
    if (selectedTable?.name === name && selectedTable?.schema === schema) {
      setSelectedTable(null)
      setPreviewData(null)
      return
    }
    setSelectedTable({ name, schema })
    setPreviewLoading(true)
    try {
      const result = await previewTable(name, 50, schema)
      setPreviewData(result)
    } catch {
      setPreviewData(null)
    } finally {
      setPreviewLoading(false)
    }
  }

  // Group tables by schema
  const publicTables = tables.filter(t => !t.schema || t.schema === 'public')
  const analyticsTables = tables.filter(t => t.schema === 'public_analytics')

  const filteredPublic = search
    ? publicTables.filter(t => t.table_name.toLowerCase().includes(search.toLowerCase()))
    : publicTables
  const filteredAnalytics = search
    ? analyticsTables.filter(t => t.table_name.toLowerCase().includes(search.toLowerCase()))
    : analyticsTables

  const isSelected = (name: string, schema: string) =>
    selectedTable?.name === name && selectedTable?.schema === schema

  const renderTableList = (tables: TableInfo[], schema: string) =>
    tables.map(t => {
      const selected = isSelected(t.table_name, schema)
      return (
        <div key={`${schema}.${t.table_name}`}>
          <button
            onClick={() => handleSelectTable(t.table_name, schema)}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-btn text-left text-sm transition-colors ${
              selected ? 'bg-primary/10 text-primary' : 'hover:bg-surface text-text-dark'
            }`}
          >
            <Table2 size={14} className={selected ? 'text-primary' : 'text-text-muted'} />
            <span className="flex-1 font-medium truncate">{t.table_name}</span>
            <span className="badge badge-info text-[9px]">{t.row_count.toLocaleString()}</span>
            <ChevronRight size={12} className={`transition-transform ${selected ? 'rotate-90' : ''}`} />
          </button>
          {selected && t.columns.length > 0 && (
            <div className="ml-6 mt-1 mb-2 space-y-0.5">
              {t.columns.map(c => {
                const IconComp = TYPE_ICONS[c.data_type] || Type
                return (
                  <div key={c.column_name} className="flex items-center gap-2 px-2 py-1 text-xs text-text-muted">
                    <IconComp size={11} className="flex-shrink-0" />
                    <span className="flex-1 truncate">{c.column_name}</span>
                    <span className="text-[10px] text-text-light">{c.data_type.slice(0, 15)}</span>
                  </div>
                )
              })}
              <div className="text-[10px] text-text-light px-2 mt-1">Tamano: {t.size}</div>
            </div>
          )}
        </div>
      )
    })

  return (
    <div className="animate-fade-in">
      <h1 className="text-2xl font-bold text-text-dark mb-1">Explorador de Datos</h1>
      <p className="text-sm text-text-muted mb-4">
        Navega las tablas y columnas disponibles (public + analytics)
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : (
        <div className="flex gap-6">
          {/* Table list */}
          <div className="w-80 flex-shrink-0">
            <div className="relative mb-3">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
              <input
                className="input pl-8 text-sm"
                placeholder="Buscar tabla..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            {/* Analytics tables */}
            {filteredAnalytics.length > 0 && (
              <>
                <h2 className="text-sm font-semibold mb-2 flex items-center gap-1.5 text-primary">
                  <Database size={14} />
                  analytics ({filteredAnalytics.length})
                </h2>
                <div className="space-y-0.5 mb-4">
                  {renderTableList(filteredAnalytics, 'public_analytics')}
                </div>
              </>
            )}

            {/* Public tables */}
            <h2 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <Database size={14} className="text-text-muted" />
              public ({filteredPublic.length})
            </h2>
            <div className="space-y-0.5">
              {renderTableList(filteredPublic, 'public')}
            </div>

            {filteredPublic.length === 0 && filteredAnalytics.length === 0 && (
              <p className="text-sm text-text-muted text-center py-8">
                {tables.length === 0 ? 'No se encontraron tablas' : 'Sin resultados para la busqueda'}
              </p>
            )}
          </div>

          {/* Preview panel */}
          <div className="flex-1 min-w-0">
            {!selectedTable ? (
              <div className="card p-8 text-center">
                <Database size={48} className="text-text-light mx-auto mb-3" />
                <p className="text-text-muted text-sm">Selecciona una tabla para ver la vista previa</p>
              </div>
            ) : previewLoading ? (
              <div className="card p-8 text-center">
                <Loader2 size={24} className="animate-spin text-primary mx-auto" />
              </div>
            ) : previewData ? (
              <div className="card p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold flex items-center gap-1.5">
                    <Table2 size={14} className="text-primary" />
                    {selectedTable.schema !== 'public' && (
                      <span className="text-primary">{selectedTable.schema}.</span>
                    )}
                    {selectedTable.name}
                  </h3>
                  <span className="text-xs text-text-muted">{previewData.total} filas (preview)</span>
                </div>
                <DataTable data={previewData.data} columns={previewData.columns} pageSize={20} />
              </div>
            ) : (
              <div className="card p-8 text-center">
                <p className="text-text-muted text-sm">No se pudo cargar la vista previa</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
