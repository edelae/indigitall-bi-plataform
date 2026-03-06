import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Send, Download, Bookmark, BarChart3, LineChart, PieChart,
  AreaChart, Table2, Loader2, Code, Sparkles, Database,
  ScatterChart, Layers, Activity, Triangle, Grid3X3,
  GitBranch, Gauge, BarChartHorizontal,
} from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChartWidget from '../components/ChartWidget'
import DataTable from '../components/DataTable'
import KpiCard from '../components/KpiCard'
import type { ChatMessage as ChatMsg, QueryResult, ChartType, TableInfo } from '../types'
import { sendChat, saveQuery, getQuery, listTables } from '../api/client'
import { PRIMARY_COLOR } from '../types'

const CHART_TYPES: { type: ChartType; icon: typeof BarChart3; label: string }[] = [
  { type: 'bar', icon: BarChart3, label: 'Barras' },
  { type: 'bar_horizontal', icon: BarChartHorizontal, label: 'Horizontal' },
  { type: 'bar_stacked', icon: Layers, label: 'Apiladas' },
  { type: 'line', icon: LineChart, label: 'Linea' },
  { type: 'pie', icon: PieChart, label: 'Torta' },
  { type: 'area', icon: AreaChart, label: 'Area' },
  { type: 'area_stacked', icon: Layers, label: 'Area Apilada' },
  { type: 'scatter', icon: ScatterChart, label: 'Dispersion' },
  { type: 'combo', icon: Activity, label: 'Combinada' },
  { type: 'funnel', icon: Triangle, label: 'Funnel' },
  { type: 'treemap', icon: Grid3X3, label: 'Treemap' },
  { type: 'gauge', icon: Gauge, label: 'Gauge' },
  { type: 'table', icon: Table2, label: 'Tabla' },
]

const SUGGESTIONS = [
  'Dame un resumen general de los datos',
  'Cual es la tasa de fallback del bot?',
  'Mensajes por hora del dia',
  'Top 10 contactos mas activos',
  'Rendimiento de agentes',
  'Tendencia de mensajes en el tiempo',
  'Crea una tarjeta KPI con el total de mensajes',
  'KPIs del Contact Center',
]

export default function QueryChat() {
  const [searchParams] = useSearchParams()
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedChart, setSelectedChart] = useState<ChartType>('bar')
  const [lastResult, setLastResult] = useState<QueryResult | null>(null)
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState<'chart' | 'source'>('chart')
  const [tables, setTables] = useState<TableInfo[]>([])
  const [tableSearch, setTableSearch] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Load tables for source panel
  useEffect(() => {
    listTables().then(setTables).catch(() => {})
  }, [])

  // Handle ?rerun=id or ?q=text
  useEffect(() => {
    const rerunId = searchParams.get('rerun')
    const question = searchParams.get('q')
    if (rerunId) {
      getQuery(parseInt(rerunId)).then(query => {
        if (query.conversation_history?.length) {
          setMessages(query.conversation_history.map(m => ({
            ...m,
            result: m.role === 'assistant' && query.result_data?.length ? {
              response: m.content,
              data: query.result_data,
              columns: (query.result_columns || []).map(c => c.name),
              chart_type: (query.visualizations?.[0]?.type) || null,
              query_details: query.generated_sql ? { sql: query.generated_sql } : null,
            } : undefined,
          })))
        } else if (query.query_text) {
          handleSend(query.query_text)
        }
      }).catch(() => {})
    } else if (question) {
      handleSend(question)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const scrollToBottom = useCallback(() => {
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }, [])

  const handleSend = async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')
    setSaved(false)
    const userMsg: ChatMsg = { role: 'user', content: msg }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setLoading(true)
    scrollToBottom()

    try {
      const result = await sendChat(msg, newMessages.filter(m => !m.result))
      const assistantMsg: ChatMsg = { role: 'assistant', content: result.response, result }
      setMessages(prev => [...prev, assistantMsg])
      setLastResult(result)
      if (result.chart_type && result.chart_type !== 'table') {
        setSelectedChart(result.chart_type as ChartType)
      }
      if (result.data?.length) setActiveTab('chart')
    } catch (err: any) {
      const errorMsg: ChatMsg = { role: 'assistant', content: `Error: ${err.message || 'No se pudo procesar la consulta'}` }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
      scrollToBottom()
    }
  }

  const handleSave = async () => {
    if (!lastResult || !messages.length) return
    const lastUser = [...messages].reverse().find(m => m.role === 'user')
    if (!lastUser) return
    try {
      await saveQuery({
        name: lastUser.content.slice(0, 80),
        query_text: lastUser.content,
        data: lastResult.data,
        columns: lastResult.columns,
        ai_function: lastResult.query_details?.function || null,
        generated_sql: lastResult.query_details?.sql || null,
        chart_type: selectedChart,
        conversation_history: messages,
      })
      setSaved(true)
    } catch { /* ignore */ }
  }

  const handleExport = () => {
    if (!lastResult?.data?.length || !lastResult.columns.length) return
    const cols = lastResult.columns
    const csv = [
      cols.join(','),
      ...lastResult.data.map(row => cols.map(c => `"${String(row[c] ?? '')}"`).join(',')),
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'consulta_resultado.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const hasData = !!lastResult?.data?.length && lastResult.columns.length >= 2
  const isKpi = lastResult?.chart_type === 'kpi' || selectedChart === 'kpi'

  // Filtered tables for source panel
  const filteredTables = tableSearch
    ? tables.filter(t => t.table_name.toLowerCase().includes(tableSearch.toLowerCase()))
    : tables

  return (
    <div className="animate-fade-in flex gap-6 h-[calc(100vh-88px)]">
      {/* Left: Chat Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {messages.length === 0 && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={18} className="text-primary" />
              <h2 className="text-lg font-semibold">Asistente IA</h2>
            </div>
            <p className="text-sm text-text-muted mb-4">
              Pregunta sobre tus datos. Puedes pedir graficas, tablas o tarjetas KPI.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  className="text-xs px-3 py-1.5 rounded-pill border border-border hover:bg-primary/5 hover:border-primary/30 text-text-muted hover:text-primary transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto pr-2">
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content}>
              {msg.result?.data?.length ? (
                <div className="text-xs text-text-muted mt-1">
                  {msg.result.data.length} filas
                  {msg.result.query_details?.function && (
                    <span className="badge badge-primary ml-2">{msg.result.query_details.function}</span>
                  )}
                </div>
              ) : null}
            </ChatMessage>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-text-muted text-sm mb-4 animate-pulse-dot">
              <Loader2 size={16} className="animate-spin" /> Procesando consulta...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="mt-3 flex gap-2">
          <input
            className="input flex-1"
            placeholder="Escribe tu pregunta aqui..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button className="btn-primary flex items-center gap-1" onClick={() => handleSend()} disabled={loading || !input.trim()}>
            <Send size={16} />
          </button>
        </div>
      </div>

      {/* Right: Results Panel */}
      <div className="w-[55%] flex flex-col min-w-0 border-l border-border-light pl-6">
        {!lastResult ? (
          <div className="flex-1 flex items-center justify-center text-center">
            <div>
              <BarChart3 size={48} className="text-text-light mx-auto mb-3" />
              <p className="text-text-muted text-sm">Los resultados apareceran aqui</p>
            </div>
          </div>
        ) : (
          <>
            {/* Tabs: Grafica | Fuente de Datos */}
            <div className="flex items-center gap-1 mb-4 border-b border-border-light pb-2">
              {(['chart', 'source'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-btn transition-colors ${
                    activeTab === tab ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'
                  }`}
                >
                  {tab === 'chart' ? 'Grafica' : 'Fuente de Datos'}
                </button>
              ))}
              <div className="ml-auto flex gap-1">
                <button onClick={handleSave} disabled={saved || !lastResult.data.length} className={`btn-ghost text-xs flex items-center gap-1 ${saved ? 'text-secondary' : ''}`}>
                  <Bookmark size={14} /> {saved ? 'Guardado' : 'Guardar'}
                </button>
                <button onClick={handleExport} disabled={!lastResult.data.length} className="btn-ghost text-xs flex items-center gap-1">
                  <Download size={14} /> CSV
                </button>
              </div>
            </div>

            {/* CHART TAB: Chart type selector + chart (60%) + table (40%) */}
            {activeTab === 'chart' && (
              <div className="flex-1 overflow-y-auto">
                {/* Chart type selector */}
                {hasData && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {CHART_TYPES.map(({ type, icon: Icon, label }) => (
                      <button
                        key={type}
                        onClick={() => setSelectedChart(type)}
                        className={`flex items-center gap-1 px-2 py-1 text-[11px] rounded-btn transition-colors ${
                          selectedChart === type
                            ? 'bg-primary text-white'
                            : 'bg-surface text-text-muted hover:bg-gray-200'
                        }`}
                      >
                        <Icon size={12} /> {label}
                      </button>
                    ))}
                  </div>
                )}

                {/* KPI Card */}
                {isKpi && lastResult.data.length > 0 && (
                  <div className="card p-6 mb-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {lastResult.data.slice(0, 6).map((row, i) => {
                        const keys = lastResult.columns
                        const label = String(row[keys[0]] || '')
                        const value = row[keys[1]] ?? row[keys[0]]
                        return (
                          <KpiCard
                            key={i}
                            label={label}
                            value={value}
                            icon={BarChart3}
                            color={PRIMARY_COLOR}
                          />
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Chart */}
                {hasData && selectedChart !== 'table' && !isKpi && (
                  <div className="card p-4 mb-4">
                    <ChartWidget
                      data={lastResult.data}
                      columns={lastResult.columns}
                      chartType={selectedChart}
                      height={320}
                    />
                  </div>
                )}

                {/* Data table always visible below chart */}
                {lastResult.data.length > 0 && (
                  <div className="card p-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold text-text-muted">
                        Datos ({lastResult.data.length} filas x {lastResult.columns.length} cols)
                      </p>
                    </div>
                    <DataTable data={lastResult.data} columns={lastResult.columns} />
                  </div>
                )}

                {lastResult.data.length === 0 && (
                  <p className="text-center text-text-muted py-8 text-sm">Sin datos</p>
                )}
              </div>
            )}

            {/* SOURCE TAB: Tables + SQL + Preview */}
            {activeTab === 'source' && (
              <div className="flex-1 overflow-y-auto">
                {/* Section 1: Table tree */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Database size={14} className="text-primary" />
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                      Tablas Disponibles ({tables.length})
                    </p>
                  </div>
                  <input
                    className="input text-xs mb-2"
                    placeholder="Buscar tabla..."
                    value={tableSearch}
                    onChange={e => setTableSearch(e.target.value)}
                  />
                  <div className="max-h-64 overflow-y-auto border border-border-light rounded-btn">
                    {filteredTables.length === 0 ? (
                      <p className="text-xs text-text-light p-3">
                        {tables.length === 0 ? 'Cargando tablas...' : 'Sin resultados'}
                      </p>
                    ) : (
                      filteredTables.map(t => (
                        <details key={`${t.schema || 'public'}.${t.table_name}`} className="border-b border-border-light last:border-b-0">
                          <summary className="flex items-center justify-between text-xs py-2 px-3 cursor-pointer hover:bg-surface">
                            <span className="font-medium text-text-dark">
                              {t.schema && t.schema !== 'public' ? (
                                <span className="text-primary">{t.schema}.</span>
                              ) : null}
                              {t.table_name}
                            </span>
                            <span className="badge badge-info text-[9px]">{t.row_count.toLocaleString()}</span>
                          </summary>
                          <div className="bg-surface/50 px-3 pb-2">
                            {t.columns.map(c => (
                              <div key={c.column_name} className="flex justify-between text-[10px] py-0.5 px-1 text-text-muted">
                                <span>{c.column_name}</span>
                                <span className="text-text-light">{c.data_type.slice(0, 15)}</span>
                              </div>
                            ))}
                            {t.size && <div className="text-[10px] text-text-light px-1 mt-1">Tamano: {t.size}</div>}
                          </div>
                        </details>
                      ))
                    )}
                  </div>
                </div>

                {/* Section 2: SQL ejecutado */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Code size={14} className="text-primary" />
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">SQL Ejecutado</p>
                  </div>
                  <div className="flex gap-2 mb-2">
                    {lastResult.query_details?.function && (
                      <span className="badge badge-primary">Funcion: {lastResult.query_details.function}</span>
                    )}
                    {lastResult.query_details?.sql && (
                      <span className="badge badge-warning">SQL Ad-hoc</span>
                    )}
                    {lastResult.data.length > 0 && (
                      <span className="badge badge-info">{lastResult.data.length} filas</span>
                    )}
                  </div>
                  <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-btn text-xs overflow-x-auto max-h-48 font-mono whitespace-pre-wrap">
                    {lastResult.query_details?.sql
                      || (lastResult.query_details?.function
                        ? `-- Funcion pre-construida: ${lastResult.query_details.function}\n-- Las funciones pre-construidas ejecutan queries optimizados internamente`
                        : '-- Sin SQL disponible')}
                  </pre>
                </div>

                {/* Section 3: Preview (max 6 rows) */}
                {lastResult.data.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                      Vista Previa (max 6 registros)
                    </p>
                    <DataTable
                      data={lastResult.data.slice(0, 6)}
                      columns={lastResult.columns}
                      pageSize={6}
                    />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
