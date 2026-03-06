import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Send, Download, Bookmark, BarChart3, LineChart, PieChart,
  AreaChart, Table2, Loader2, Code, Sparkles, Database,
} from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChartWidget from '../components/ChartWidget'
import DataTable from '../components/DataTable'
import type { ChatMessage as ChatMsg, QueryResult, ChartType } from '../types'
import { sendChat, saveQuery, getQuery, listTables } from '../api/client'
import type { TableInfo } from '../types'

const CHART_TYPES: { type: ChartType; icon: typeof BarChart3; label: string }[] = [
  { type: 'bar', icon: BarChart3, label: 'Barras' },
  { type: 'line', icon: LineChart, label: 'Linea' },
  { type: 'pie', icon: PieChart, label: 'Torta' },
  { type: 'area', icon: AreaChart, label: 'Area' },
  { type: 'table', icon: Table2, label: 'Tabla' },
]

const SUGGESTIONS = [
  'Dame un resumen general de los datos',
  'Cual es la tasa de fallback del bot?',
  'Mensajes por hora del dia',
  'Top 10 contactos mas activos',
  'Rendimiento de agentes',
  'Tendencia de mensajes en el tiempo',
  'Distribucion de intenciones del bot',
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
  const [activeTab, setActiveTab] = useState<'chart' | 'table' | 'source'>('chart')
  const [tables, setTables] = useState<TableInfo[]>([])
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
      const result = await sendChat(
        msg,
        newMessages.filter(m => !m.result), // Send clean history
      )

      const assistantMsg: ChatMsg = {
        role: 'assistant',
        content: result.response,
        result,
      }
      setMessages(prev => [...prev, assistantMsg])
      setLastResult(result)
      if (result.chart_type && result.chart_type !== 'table') {
        setSelectedChart(result.chart_type as ChartType)
      }
      if (result.data?.length) {
        setActiveTab('chart')
      }
    } catch (err: any) {
      const errorMsg: ChatMsg = {
        role: 'assistant',
        content: `Error: ${err.message || 'No se pudo procesar la consulta'}`,
      }
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
    } catch {
      // ignore
    }
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

  return (
    <div className="animate-fade-in flex gap-6 h-[calc(100vh-88px)]">
      {/* Left: Chat Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Suggestion chips (only when empty) */}
        {messages.length === 0 && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={18} className="text-primary" />
              <h2 className="text-lg font-semibold">Asistente IA</h2>
            </div>
            <p className="text-sm text-text-muted mb-4">
              Pregunta lo que quieras sobre tus datos. El asistente genera SQL, ejecuta consultas y muestra graficas automaticamente.
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

        {/* Messages */}
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
              <Loader2 size={16} className="animate-spin" />
              Procesando consulta...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="mt-3 flex gap-2">
          <input
            className="input flex-1"
            placeholder="Escribe tu pregunta aqui..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button
            className="btn-primary flex items-center gap-1"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
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
              <p className="text-text-muted text-sm">
                Los resultados de tus consultas apareceran aqui
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div className="flex items-center gap-1 mb-4 border-b border-border-light pb-2">
              {(['chart', 'table', 'source'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-btn transition-colors ${
                    activeTab === tab
                      ? 'bg-primary/10 text-primary'
                      : 'text-text-muted hover:bg-surface'
                  }`}
                >
                  {tab === 'chart' ? 'Grafica' : tab === 'table' ? 'Tabla' : 'Fuente de Datos'}
                </button>
              ))}

              <div className="ml-auto flex gap-1">
                <button
                  onClick={handleSave}
                  disabled={saved || !lastResult.data.length}
                  className={`btn-ghost text-xs flex items-center gap-1 ${saved ? 'text-secondary' : ''}`}
                >
                  <Bookmark size={14} />
                  {saved ? 'Guardado' : 'Guardar'}
                </button>
                <button
                  onClick={handleExport}
                  disabled={!lastResult.data.length}
                  className="btn-ghost text-xs flex items-center gap-1"
                >
                  <Download size={14} />
                  CSV
                </button>
              </div>
            </div>

            {/* Chart type selector */}
            {activeTab === 'chart' && hasData && (
              <div className="flex gap-1 mb-3">
                {CHART_TYPES.map(({ type, icon: Icon, label }) => (
                  <button
                    key={type}
                    onClick={() => setSelectedChart(type)}
                    className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded-btn transition-colors ${
                      selectedChart === type
                        ? 'bg-primary text-white'
                        : 'bg-surface text-text-muted hover:bg-gray-200'
                    }`}
                  >
                    <Icon size={13} />
                    {label}
                  </button>
                ))}
              </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'chart' && hasData && selectedChart !== 'table' && (
                <div className="card p-4">
                  <ChartWidget
                    data={lastResult.data}
                    columns={lastResult.columns}
                    chartType={selectedChart}
                    height={350}
                  />
                </div>
              )}

              {(activeTab === 'table' || (activeTab === 'chart' && (selectedChart === 'table' || !hasData))) && (
                <div className="card p-3">
                  {lastResult.data.length > 0 ? (
                    <DataTable
                      data={lastResult.data}
                      columns={lastResult.columns}
                    />
                  ) : (
                    <p className="text-center text-text-muted py-8 text-sm">Sin datos</p>
                  )}
                </div>
              )}

              {activeTab === 'source' && (
                <div className="flex gap-4">
                  {/* Table sidebar */}
                  <div className="w-52 flex-shrink-0 border-r border-border-light pr-3 max-h-[500px] overflow-y-auto">
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                      Tablas
                    </p>
                    {tables.length === 0 ? (
                      <p className="text-xs text-text-light">Cargando tablas...</p>
                    ) : (
                      tables.map(t => (
                        <details key={t.table_name} className="mb-1">
                          <summary className="flex items-center justify-between text-xs py-1.5 px-2 rounded cursor-pointer hover:bg-surface">
                            <span className="font-medium text-text-dark">{t.table_name}</span>
                            <span className="badge badge-info text-[9px]">{t.row_count}</span>
                          </summary>
                          <div className="ml-2 mt-1">
                            {t.columns.map(c => (
                              <div key={c.column_name} className="flex justify-between text-[10px] py-0.5 px-2 text-text-muted">
                                <span>{c.column_name}</span>
                                <span className="text-text-light">{c.data_type.slice(0, 12)}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      ))
                    )}
                  </div>

                  {/* SQL + metadata */}
                  <div className="flex-1 min-w-0">
                    {/* Badges */}
                    <div className="flex gap-2 mb-3">
                      {lastResult.query_details?.function && (
                        <span className="badge badge-primary">
                          Funcion: {lastResult.query_details.function}
                        </span>
                      )}
                      {lastResult.data.length > 0 && (
                        <span className="badge badge-info">
                          {lastResult.data.length} filas x {lastResult.columns.length} columnas
                        </span>
                      )}
                      {lastResult.query_details?.sql && (
                        <span className="badge badge-warning">SQL Ad-hoc</span>
                      )}
                    </div>

                    {/* SQL */}
                    <div className="mb-3">
                      <p className="text-[11px] font-semibold text-text-muted mb-1 flex items-center gap-1">
                        <Code size={12} />
                        SQL Ejecutado
                      </p>
                      <pre className="bg-[#1A1A2E] text-gray-300 p-3 rounded-btn text-xs overflow-x-auto max-h-40 font-mono">
                        {lastResult.query_details?.sql
                          || (lastResult.query_details?.function
                            ? `-- Funcion pre-construida: ${lastResult.query_details.function}`
                            : '-- Sin SQL disponible')}
                      </pre>
                    </div>

                    {/* Results */}
                    {lastResult.data.length > 0 && (
                      <DataTable
                        data={lastResult.data}
                        columns={lastResult.columns}
                        compact
                        pageSize={20}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
