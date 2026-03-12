import { useState } from 'react'
import { Calendar, ArrowUpDown, Hash, Database, ChevronDown, Loader2 } from 'lucide-react'
import { executeSql } from '../api/client'
import type { QueryResult } from '../types'

interface Props {
  sql: string
  lastResult: QueryResult
  onResultUpdate: (result: QueryResult) => void
}

type Granularity = 'month' | 'week' | 'day'

const GRAN_LABELS: Record<Granularity, string> = {
  month: 'Mes',
  week: 'Semana',
  day: 'Dia',
}

/** Available table columns for reference */
const TABLE_COLUMNS: Record<string, string[]> = {
  messages: [
    'date', 'hour', 'day_of_week', 'direction', 'send_type', 'content_type',
    'status', 'contact_name', 'contact_id', 'conversation_id', 'agent_id',
    'intent', 'is_fallback', 'is_bot', 'is_human', 'wait_time_seconds',
    'handle_time_seconds',
  ],
  chat_conversations: [
    'session_id', 'conversation_session_id', 'contact_id', 'agent_id',
    'agent_email', 'channel', 'queued_at', 'assigned_at', 'closed_at',
    'wait_time_seconds', 'handle_time_seconds',
  ],
  nps_surveys: [
    'date', 'hour', 'contact_name', 'entity', 'score_atencion', 'score_asesor',
    'nps_categoria', 'canal_tipo', 'agent_id', 'close_reason',
  ],
  daily_stats: [
    'date', 'total_messages', 'unique_contacts', 'conversations', 'fallback_count',
  ],
  contacts: [
    'contact_id', 'contact_name', 'total_messages', 'first_contact', 'last_contact',
  ],
}

export default function SqlVariables({ sql, lastResult, onResultUpdate }: Props) {
  const [loading, setLoading] = useState(false)
  const [expandedTable, setExpandedTable] = useState<string | null>(null)

  // Detect DATE_TRUNC granularity
  const granMatch = sql.match(/DATE_TRUNC\s*\(\s*'(month|week|day)'/i)
  const currentGran = (granMatch?.[1] || null) as Granularity | null

  // Detect LIMIT
  const limitMatch = sql.match(/LIMIT\s+(\d+)/i)
  const currentLimit = limitMatch ? parseInt(limitMatch[1]) : null

  // Detect ORDER BY direction
  const orderMatch = sql.match(/ORDER\s+BY\s+.+?(ASC|DESC)/i)
  const currentOrder = orderMatch?.[1]?.toUpperCase() || null

  // Detect referenced tables
  const tablePattern = /(?:FROM|JOIN)\s+([a-zA-Z_]\w*)/gi
  const referencedTables: string[] = []
  let m: RegExpExecArray | null
  while ((m = tablePattern.exec(sql)) !== null) {
    const t = m[1].toLowerCase()
    if (TABLE_COLUMNS[t] && !referencedTables.includes(t)) referencedTables.push(t)
  }

  // Detect columns used in SELECT
  const selectMatch = sql.match(/SELECT\s+([\s\S]*?)\s+FROM/i)
  const selectClause = selectMatch?.[1] || ''

  const executeNewSql = async (newSql: string) => {
    setLoading(true)
    try {
      const res = await executeSql(newSql)
      onResultUpdate({
        ...lastResult,
        data: res.data,
        columns: res.columns,
        query_details: { ...lastResult.query_details, sql: newSql },
      })
    } catch (err: any) {
      alert('Error: ' + (err.message || 'Error desconocido'))
    } finally {
      setLoading(false)
    }
  }

  const changeGranularity = (gran: Granularity) => {
    if (gran === currentGran) return
    const newSql = sql.replace(
      /DATE_TRUNC\s*\(\s*'(month|week|day)'/gi,
      `DATE_TRUNC('${gran}'`
    )
    executeNewSql(newSql)
  }

  const changeLimit = (limit: number) => {
    if (limit === currentLimit) return
    const newSql = sql.replace(/LIMIT\s+\d+/i, `LIMIT ${limit}`)
    executeNewSql(newSql)
  }

  const toggleOrder = () => {
    const newDir = currentOrder === 'DESC' ? 'ASC' : 'DESC'
    const newSql = sql.replace(/(ORDER\s+BY\s+.+?)(ASC|DESC)/i, `$1${newDir}`)
    executeNewSql(newSql)
  }

  const insertColumnInSql = (col: string) => {
    // Copy column name to clipboard for easy paste into SQL editor
    navigator.clipboard.writeText(col).catch(() => {})
  }

  const hasAnyControl = currentGran || currentLimit || currentOrder || referencedTables.length > 0

  if (!hasAnyControl) return null

  return (
    <div className="space-y-3">
      {loading && (
        <div className="flex items-center gap-1.5 text-xs text-primary">
          <Loader2 size={12} className="animate-spin" /> Ejecutando...
        </div>
      )}

      {/* Granularity */}
      {currentGran && (
        <section>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Calendar size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Granularidad temporal
            </p>
          </div>
          <div className="flex gap-1">
            {(['month', 'week', 'day'] as Granularity[]).map(g => (
              <button
                key={g}
                onClick={() => changeGranularity(g)}
                disabled={loading}
                className={`flex-1 px-2 py-1.5 rounded-btn text-[10px] font-medium transition-colors ${
                  currentGran === g ? 'bg-primary text-white' : 'hover:bg-surface'
                }`}
                style={currentGran !== g ? { backgroundColor: 'var(--bg-surface)', color: 'var(--text-muted)' } : {}}
              >
                {GRAN_LABELS[g]}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Limit */}
      {currentLimit && (
        <section>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Hash size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Limite de filas
            </p>
          </div>
          <div className="flex gap-1">
            {[10, 25, 50, 100, 500].map(n => (
              <button
                key={n}
                onClick={() => changeLimit(n)}
                disabled={loading}
                className={`flex-1 px-1 py-1.5 rounded-btn text-[10px] font-medium transition-colors ${
                  currentLimit === n ? 'bg-primary text-white' : 'hover:bg-surface'
                }`}
                style={currentLimit !== n ? { backgroundColor: 'var(--bg-surface)', color: 'var(--text-muted)' } : {}}
              >
                {n}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Sort direction */}
      {currentOrder && (
        <section>
          <div className="flex items-center gap-1.5 mb-1.5">
            <ArrowUpDown size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Ordenamiento
            </p>
          </div>
          <button
            onClick={toggleOrder}
            disabled={loading}
            className="w-full px-2 py-1.5 rounded-btn text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          >
            {currentOrder === 'DESC' ? '↓ Mayor a menor' : '↑ Menor a mayor'} — Clic para invertir
          </button>
        </section>
      )}

      {/* Available columns from referenced tables */}
      {referencedTables.length > 0 && (
        <section>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Database size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Columnas disponibles
            </p>
          </div>
          <p className="text-[9px] mb-1.5" style={{ color: 'var(--text-light)' }}>
            Clic para copiar. Pega en el editor SQL.
          </p>
          {referencedTables.map(table => (
            <div key={table} className="mb-1">
              <button
                onClick={() => setExpandedTable(expandedTable === table ? null : table)}
                className="w-full flex items-center justify-between px-2 py-1 rounded-btn text-[10px] font-medium hover:bg-surface transition-colors"
                style={{ color: 'var(--text-primary)' }}
              >
                <span className="text-primary font-semibold">{table}</span>
                <ChevronDown
                  size={10}
                  className={`transition-transform ${expandedTable === table ? 'rotate-180' : ''}`}
                  style={{ color: 'var(--text-light)' }}
                />
              </button>
              {expandedTable === table && (
                <div className="flex flex-wrap gap-1 px-1 py-1">
                  {TABLE_COLUMNS[table]?.map(col => {
                    const isUsed = selectClause.toLowerCase().includes(col.toLowerCase())
                    return (
                      <button
                        key={col}
                        onClick={() => insertColumnInSql(col)}
                        className={`px-1.5 py-0.5 rounded text-[9px] transition-colors ${
                          isUsed
                            ? 'bg-primary/15 text-primary font-semibold'
                            : 'bg-[var(--bg-surface)] hover:bg-primary/10'
                        }`}
                        style={!isUsed ? { color: 'var(--text-muted)' } : {}}
                        title={`Copiar "${col}"`}
                      >
                        {col}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
