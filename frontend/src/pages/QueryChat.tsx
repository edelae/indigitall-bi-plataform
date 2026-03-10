import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Send, Download, Bookmark, BarChart3, Loader2, Code, Sparkles, Database,
  Table2, Settings2,
} from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChartWidget from '../components/ChartWidget'
import DataTable from '../components/DataTable'
import KpiCard from '../components/KpiCard'
import ChartCustomizer, { type ChartConfig } from '../components/ChartCustomizer'
import type { ChatMessage as ChatMsg, QueryResult, ChartType, TableInfo } from '../types'
import { sendChat, saveQuery, getQuery, listTables } from '../api/client'
import { PRIMARY_COLOR, COLOR_PALETTES } from '../types'

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
  const [showCustomizer, setShowCustomizer] = useState(false)
  const [chartConfig, setChartConfig] = useState<ChartConfig>({
    chartType: 'bar',
    showLegend: true,
  })
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
        const cols = (query.result_columns || []).map(c => c.name)
        const chartType = (query.visualizations?.[0]?.type) || null
        const restoredResult: QueryResult | null = query.result_data?.length ? {
          response: '',
          data: query.result_data,
          columns: cols,
          chart_type: chartType,
          query_details: query.generated_sql ? { sql: query.generated_sql, title: query.name } : null,
        } : null

        if (restoredResult) {
          setLastResult(restoredResult)
          if (chartType && chartType !== 'table') {
            setSelectedChart(chartType as ChartType)
            setChartConfig(prev => ({ ...prev, chartType: chartType as ChartType }))
          }
          setActiveTab('chart')
        }

        if (query.conversation_history?.length) {
          setMessages(query.conversation_history.map(m => ({
            ...m,
            result: m.role === 'assistant' && restoredResult ? restoredResult : undefined,
          })))
        } else if (restoredResult && query.query_text) {
          setMessages([
            { role: 'user', content: query.query_text },
            { role: 'assistant', content: restoredResult.response || `Resultado: ${query.name}`, result: restoredResult },
          ])
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
        setChartConfig(prev => ({ ...prev, chartType: result.chart_type as ChartType }))
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
        chart_type: chartConfig.chartType,
        conversation_history: messages,
      })
      setSaved(true)
    } catch { /* ignore */ }
  }

  const handleExport = () => {
    if (!lastResult?.data?.length || !lastResult.columns.length) return
    const cols = lastResult.columns
    const bom = '\uFEFF'
    const csv = [
      cols.join(','),
      ...lastResult.data.map(row => cols.map(c => `"${String(row[c] ?? '')}"`).join(',')),
    ].join('\n')
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `consulta_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleConfigChange = (newConfig: ChartConfig) => {
    setChartConfig(newConfig)
    if (newConfig.chartType !== selectedChart) {
      setSelectedChart(newConfig.chartType)
    }
  }

  const hasData = !!lastResult?.data?.length && lastResult.columns.length >= 2
  const isKpi = lastResult?.chart_type === 'kpi' || selectedChart === 'kpi'

  // Filtered tables for source panel
  const filteredTables = tableSearch
    ? tables.filter(t => t.table_name.toLowerCase().includes(tableSearch.toLowerCase()))
    : tables

  // Resolve colors from palette
  const chartColors = chartConfig.colorPalette
    ? COLOR_PALETTES[chartConfig.colorPalette]?.colors
    : undefined

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
            <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
              Pregunta sobre tus datos. Puedes pedir graficas, tablas o tarjetas KPI.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  className="text-xs px-3 py-1.5 rounded-pill transition-colors"
                  style={{
                    border: '1px solid var(--border)',
                    color: 'var(--text-muted)',
                  }}
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
                <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  {msg.result.data.length} filas
                  {msg.result.query_details?.function && (
                    <span className="badge badge-primary ml-2">{msg.result.query_details.function}</span>
                  )}
                </div>
              ) : null}
            </ChatMessage>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm mb-4 animate-pulse-dot" style={{ color: 'var(--text-muted)' }}>
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
      <div className={`${showCustomizer ? 'w-[42%]' : 'w-[55%]'} flex flex-col min-w-0 border-l pl-6 transition-all`}
        style={{ borderColor: 'var(--border-light)' }}>
        {!lastResult ? (
          <div className="flex-1 flex items-center justify-center text-center">
            <div>
              <BarChart3 size={48} className="mx-auto mb-3" style={{ color: 'var(--text-light)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Los resultados apareceran aqui</p>
            </div>
          </div>
        ) : (
          <>
            {/* Tabs: Grafica | Fuente de Datos */}
            <div className="flex items-center gap-1 mb-4 border-b pb-2" style={{ borderColor: 'var(--border-light)' }}>
              {(['chart', 'source'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-btn transition-colors ${
                    activeTab === tab ? 'bg-primary/10 text-primary' : 'hover:bg-surface'
                  }`}
                  style={activeTab !== tab ? { color: 'var(--text-muted)' } : {}}
                >
                  {tab === 'chart' ? 'Grafica' : 'Fuente de Datos'}
                </button>
              ))}
              <div className="ml-auto flex gap-1">
                {hasData && !isKpi && (
                  <button
                    onClick={() => setShowCustomizer(!showCustomizer)}
                    className={`btn-ghost text-xs flex items-center gap-1 ${showCustomizer ? 'text-primary' : ''}`}
                    title="Personalizar grafica"
                  >
                    <Settings2 size={14} /> Personalizar
                  </button>
                )}
                <button onClick={handleSave} disabled={saved || !lastResult.data.length}
                  className={`btn-ghost text-xs flex items-center gap-1 ${saved ? 'text-secondary' : ''}`}>
                  <Bookmark size={14} /> {saved ? 'Guardado' : 'Guardar'}
                </button>
                <button onClick={handleExport} disabled={!lastResult.data.length}
                  className="btn-ghost text-xs flex items-center gap-1">
                  <Download size={14} /> CSV
                </button>
              </div>
            </div>

            {/* CHART TAB */}
            {activeTab === 'chart' && (
              <div className="flex-1 overflow-y-auto">
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
                      chartType={chartConfig.chartType}
                      height={320}
                      colors={chartColors}
                      xLabel={chartConfig.xLabel}
                      yLabel={chartConfig.yLabel}
                      showLegend={chartConfig.showLegend}
                      fontFamily={chartConfig.fontFamily}
                      axisFontSize={chartConfig.axisFontSize}
                      legendFontSize={chartConfig.legendFontSize}
                    />
                  </div>
                )}

                {/* Data table */}
                {lastResult.data.length > 0 && (
                  <div className="card p-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                        Datos ({lastResult.data.length} filas x {lastResult.columns.length} cols)
                      </p>
                    </div>
                    <DataTable data={lastResult.data} columns={lastResult.columns} />
                  </div>
                )}

                {lastResult.data.length === 0 && (
                  <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>Sin datos</p>
                )}
              </div>
            )}

            {/* SOURCE TAB */}
            {activeTab === 'source' && (
              <div className="flex-1 overflow-y-auto">
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Database size={14} className="text-primary" />
                    <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                      Tablas Disponibles ({tables.length})
                    </p>
                  </div>
                  <input
                    className="input text-xs mb-2"
                    placeholder="Buscar tabla..."
                    value={tableSearch}
                    onChange={e => setTableSearch(e.target.value)}
                  />
                  <div className="max-h-64 overflow-y-auto rounded-btn" style={{ border: '1px solid var(--border-light)' }}>
                    {filteredTables.length === 0 ? (
                      <p className="text-xs p-3" style={{ color: 'var(--text-light)' }}>
                        {tables.length === 0 ? 'Cargando tablas...' : 'Sin resultados'}
                      </p>
                    ) : (
                      filteredTables.map(t => (
                        <details key={`${t.schema || 'public'}.${t.table_name}`}
                          className="last:border-b-0" style={{ borderBottom: '1px solid var(--border-light)' }}>
                          <summary className="flex items-center justify-between text-xs py-2 px-3 cursor-pointer hover:bg-surface">
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {t.schema && t.schema !== 'public' ? (
                                <span className="text-primary">{t.schema}.</span>
                              ) : null}
                              {t.table_name}
                            </span>
                            <span className="badge badge-info text-[9px]">{t.row_count.toLocaleString()}</span>
                          </summary>
                          <div className="px-3 pb-2" style={{ backgroundColor: 'var(--bg-surface)' }}>
                            {t.columns.map(c => (
                              <div key={c.column_name} className="flex justify-between text-[10px] py-0.5 px-1" style={{ color: 'var(--text-muted)' }}>
                                <span>{c.column_name}</span>
                                <span style={{ color: 'var(--text-light)' }}>{c.data_type.slice(0, 15)}</span>
                              </div>
                            ))}
                            {t.size && <div className="text-[10px] px-1 mt-1" style={{ color: 'var(--text-light)' }}>Tamano: {t.size}</div>}
                          </div>
                        </details>
                      ))
                    )}
                  </div>
                </div>

                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Code size={14} className="text-primary" />
                    <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>SQL Ejecutado</p>
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
                  <pre className="p-3 rounded-btn text-xs overflow-x-auto max-h-48 font-mono whitespace-pre-wrap"
                    style={{ backgroundColor: 'var(--tooltip-bg)', color: '#D1D5DB' }}>
                    {lastResult.query_details?.sql
                      || (lastResult.query_details?.function
                        ? `-- Funcion pre-construida: ${lastResult.query_details.function}\n-- Las funciones pre-construidas ejecutan queries optimizados internamente`
                        : '-- Sin SQL disponible')}
                  </pre>
                </div>

                {lastResult.data.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
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

      {/* Chart Customizer Sidebar */}
      {showCustomizer && hasData && (
        <ChartCustomizer
          config={chartConfig}
          onChange={handleConfigChange}
          onClose={() => setShowCustomizer(false)}
        />
      )}
    </div>
  )
}
