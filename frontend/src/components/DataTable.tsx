import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'

interface Props {
  data: Record<string, any>[]
  columns: string[]
  pageSize?: number
  compact?: boolean
  onRowClick?: (row: Record<string, any>) => void
}

// Label translation
const LABELS: Record<string, string> = {
  date: 'Fecha', fecha: 'Fecha', messages: 'Mensajes', count: 'Cantidad',
  total: 'Total', name: 'Nombre', value: 'Valor', agent_name: 'Agente',
  contact_name: 'Contacto', status: 'Estado', hour: 'Hora',
}

function getLabel(col: string): string {
  const lower = col.toLowerCase()
  return LABELS[lower] || col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function DataTable({ data, columns, pageSize = 15, compact = false, onRowClick }: Props) {
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(0)

  const sortedData = useMemo(() => {
    if (!sortCol) return data
    return [...data].sort((a, b) => {
      const va = a[sortCol] ?? ''
      const vb = b[sortCol] ?? ''
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortDir === 'asc' ? va - vb : vb - va
      }
      return sortDir === 'asc'
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va))
    })
  }, [data, sortCol, sortDir])

  const totalPages = Math.ceil(sortedData.length / pageSize)
  const pagedData = sortedData.slice(page * pageSize, (page + 1) * pageSize)

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
    setPage(0)
  }

  const cellPad = compact ? 'px-2 py-1' : 'px-3 py-2'
  const fontSize = compact ? 'text-[11px]' : 'text-xs'

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-surface border-b border-border">
              {columns.map(col => (
                <th
                  key={col}
                  className={`${cellPad} text-left ${fontSize} font-semibold text-text-muted uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100`}
                  onClick={() => handleSort(col)}
                >
                  <span className="flex items-center gap-1">
                    {getLabel(col)}
                    {sortCol === col
                      ? (sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />)
                      : <ChevronsUpDown size={12} className="opacity-30" />
                    }
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagedData.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-border-light ${i % 2 ? 'bg-gray-50/50' : ''} ${
                  onRowClick ? 'cursor-pointer hover:bg-primary/5' : ''
                }`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(col => (
                  <td key={col} className={`${cellPad} ${fontSize} text-text-dark max-w-[200px] truncate`}>
                    {row[col] != null ? String(row[col]) : '\u2014'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 px-2">
          <span className="text-xs text-text-muted">
            {sortedData.length} filas — Pagina {page + 1} de {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-ghost text-xs py-1 px-2"
            >
              Anterior
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="btn-ghost text-xs py-1 px-2"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
