import { useEffect, useState } from 'react'
import {
  Database, Table2, ChevronRight, Loader2,
  Hash, Type, Calendar, ToggleLeft,
} from 'lucide-react'
import DataTable from '../components/DataTable'
import { listTables, previewTable } from '../api/client'
import type { TableInfo } from '../types'

const TYPE_ICONS: Record<string, typeof Hash> = {
  integer: Hash,
  bigint: Hash,
  numeric: Hash,
  'double precision': Hash,
  'character varying': Type,
  text: Type,
  boolean: ToggleLeft,
  'timestamp with time zone': Calendar,
  'timestamp without time zone': Calendar,
  date: Calendar,
  jsonb: Database,
  json: Database,
}

export default function DataExplorer() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [previewData, setPreviewData] = useState<{ columns: string[]; data: Record<string, any>[]; total: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    listTables()
      .then(setTables)
      .catch(() => setTables([]))
      .finally(() => setLoading(false))
  }, [])

  const handleSelectTable = async (name: string) => {
    if (selectedTable === name) {
      setSelectedTable(null)
      setPreviewData(null)
      return
    }
    setSelectedTable(name)
    setPreviewLoading(true)
    try {
      const result = await previewTable(name, 50)
      setPreviewData(result)
    } catch {
      setPreviewData(null)
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-2xl font-bold text-text-dark mb-1">Explorador de Datos</h1>
      <p className="text-sm text-text-muted mb-6">
        Navega las tablas y columnas disponibles en la base de datos
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : (
        <div className="flex gap-6">
          {/* Table list */}
          <div className="w-80 flex-shrink-0">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
              <Database size={14} className="text-primary" />
              {tables.length} Tablas
            </h2>
            <div className="space-y-1">
              {tables.map(t => {
                const isSelected = selectedTable === t.table_name
                return (
                  <div key={t.table_name}>
                    <button
                      onClick={() => handleSelectTable(t.table_name)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-btn text-left text-sm transition-colors ${
                        isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-surface text-text-dark'
                      }`}
                    >
                      <Table2 size={14} className={isSelected ? 'text-primary' : 'text-text-muted'} />
                      <span className="flex-1 font-medium truncate">{t.table_name}</span>
                      <span className="badge badge-info text-[9px]">{t.row_count.toLocaleString()}</span>
                      <ChevronRight size={12} className={`transition-transform ${isSelected ? 'rotate-90' : ''}`} />
                    </button>

                    {/* Column list (expandable) */}
                    {isSelected && t.columns.length > 0 && (
                      <div className="ml-6 mt-1 mb-2 space-y-0.5">
                        {t.columns.map(c => {
                          const IconComp = TYPE_ICONS[c.data_type] || Type
                          return (
                            <div
                              key={c.column_name}
                              className="flex items-center gap-2 px-2 py-1 text-xs text-text-muted"
                            >
                              <IconComp size={11} className="flex-shrink-0" />
                              <span className="flex-1 truncate">{c.column_name}</span>
                              <span className="text-[10px] text-text-light">{c.data_type.slice(0, 15)}</span>
                            </div>
                          )
                        })}
                        <div className="text-[10px] text-text-light px-2 mt-1">
                          Tamano: {t.size}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Preview panel */}
          <div className="flex-1 min-w-0">
            {!selectedTable ? (
              <div className="card p-8 text-center">
                <Database size={48} className="text-text-light mx-auto mb-3" />
                <p className="text-text-muted text-sm">
                  Selecciona una tabla para ver una vista previa de los datos
                </p>
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
                    {selectedTable}
                  </h3>
                  <span className="text-xs text-text-muted">{previewData.total} filas (preview)</span>
                </div>
                <DataTable
                  data={previewData.data}
                  columns={previewData.columns}
                  pageSize={20}
                />
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
