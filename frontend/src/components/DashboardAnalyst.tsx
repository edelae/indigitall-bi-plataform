import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles, Send, X, Loader2, ChevronDown, ChevronUp,
  BarChart3, TrendingUp, Users, Zap, ExternalLink, Trash2,
  Minimize2, Maximize2,
} from 'lucide-react'
import ChartWidget from './ChartWidget'
import type { ChartType, QueryResult, ChatMessage } from '../types'
import { sendChat, saveQuery } from '../api/client'

interface AnalystMessage {
  role: 'user' | 'assistant'
  content: string
  result?: QueryResult
  timestamp: string
}

interface DashboardContext {
  activeTab: string
  kpis: Record<string, string | number>
  dateRange?: { start: string; end: string }
}

interface Props {
  context?: DashboardContext
  onClose?: () => void
}

const SUGGESTED_QUESTIONS: Record<string, { icon: typeof BarChart3; text: string }[]> = {
  whatsapp: [
    { icon: TrendingUp, text: 'Cual es la tendencia de mensajes esta semana?' },
    { icon: BarChart3, text: 'Distribucion de mensajes por hora' },
    { icon: Users, text: 'Top 5 contactos mas activos' },
    { icon: Zap, text: 'Cual es la tasa de fallback del bot?' },
  ],
  bot: [
    { icon: Zap, text: 'Cuales son las intenciones mas comunes del bot?' },
    { icon: TrendingUp, text: 'Tendencia de mensajes del bot en el tiempo' },
    { icon: BarChart3, text: 'Comparacion bot vs humano en conversaciones' },
    { icon: Users, text: 'Cuantos contactos unicos ha atendido el bot?' },
  ],
  cc: [
    { icon: Users, text: 'Rendimiento de agentes del contact center' },
    { icon: TrendingUp, text: 'Tendencia del tiempo de primera respuesta' },
    { icon: BarChart3, text: 'Distribucion de razones de cierre de conversacion' },
    { icon: Zap, text: 'Cual es el FCR actual del contact center?' },
  ],
  sms: [
    { icon: TrendingUp, text: 'Tendencia de envios SMS vs chunks' },
    { icon: BarChart3, text: 'Ranking de campanas por volumen' },
    { icon: Zap, text: 'Cuales campanas tienen mejor CTR?' },
    { icon: Users, text: 'KPIs generales de SMS' },
  ],
  toques: [
    { icon: BarChart3, text: 'Distribucion de usuarios por numero de toques' },
    { icon: Users, text: 'Cuantos usuarios estan sobre-tocados?' },
    { icon: TrendingUp, text: 'Tendencia de toques en el tiempo' },
    { icon: Zap, text: 'Cual es el promedio de toques por usuario?' },
  ],
}

const DEFAULT_SUGGESTIONS = SUGGESTED_QUESTIONS.whatsapp

export default function DashboardAnalyst({ context, onClose }: Props) {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<AnalystMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(true)
  const [minimized, setMinimized] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const suggestions = SUGGESTED_QUESTIONS[context?.activeTab || ''] || DEFAULT_SUGGESTIONS

  const scrollToBottom = useCallback(() => {
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }, [])

  useEffect(() => {
    if (expanded && !minimized) inputRef.current?.focus()
  }, [expanded, minimized])

  const buildContextPrefix = (): string => {
    if (!context) return ''
    const parts: string[] = []

    const tabNames: Record<string, string> = {
      whatsapp: 'WhatsApp General',
      bot: 'Bot',
      cc: 'Contact Center',
      sms: 'SMS',
      toques: 'Control de Toques',
    }
    parts.push(`[CONTEXTO DEL DASHBOARD — tab activo: "${tabNames[context.activeTab] || context.activeTab}"]`)

    if (context.kpis && Object.keys(context.kpis).length > 0) {
      const kpiLines = Object.entries(context.kpis).map(([k, v]) => {
        const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        return `- ${label}: ${v}`
      })
      parts.push(`[DATOS REALES del dashboard (usa estos datos para responder, NO inventes datos):\n${kpiLines.join('\n')}]`)
    }

    if (context.dateRange) {
      parts.push(`[Rango de fechas seleccionado: ${context.dateRange.start} a ${context.dateRange.end}]`)
    }

    parts.push('[INSTRUCCION: Basa tu respuesta EXCLUSIVAMENTE en los datos proporcionados arriba y en consultas reales a la base de datos. NUNCA inventes numeros ni estadisticas. Si no tienes un dato, dilo claramente.]')

    return parts.join('\n') + '\n\nPregunta del usuario: '
  }

  const handleSend = async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')

    const userMsg: AnalystMessage = {
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    scrollToBottom()

    try {
      const contextPrefix = buildContextPrefix()
      const fullMessage = contextPrefix + msg

      const history: ChatMessage[] = messages
        .filter(m => !m.result)
        .map(m => ({ role: m.role, content: m.content }))

      const result = await sendChat(fullMessage, history)

      const assistantMsg: AnalystMessage = {
        role: 'assistant',
        content: result.response,
        result: result.data?.length ? result : undefined,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message || 'No se pudo procesar la consulta'}`,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
      scrollToBottom()
    }
  }

  const handleSaveAsQuery = async (msg: AnalystMessage) => {
    if (!msg.result?.data?.length) return
    try {
      const lastUser = [...messages].reverse().find(m => m.role === 'user')
      const result = await saveQuery({
        name: (lastUser?.content || 'Analisis del dashboard').slice(0, 80),
        query_text: lastUser?.content || '',
        data: msg.result.data,
        columns: msg.result.columns,
        ai_function: msg.result.query_details?.function || null,
        generated_sql: msg.result.query_details?.sql || null,
        chart_type: msg.result.chart_type,
      })
      navigate(`/consultas/nueva?rerun=${result.id}`)
    } catch { /* ignore */ }
  }

  const clearHistory = () => setMessages([])

  // Collapsed floating button
  if (minimized) {
    return createPortal(
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-6 right-6 z-[9999] flex items-center gap-2 px-4 py-3 rounded-full shadow-lg transition-all hover:scale-105"
        style={{
          backgroundColor: '#0066CC',
          color: 'white',
          fontFamily: 'Inter, sans-serif',
          boxShadow: '0 4px 20px rgba(0, 102, 204, 0.4)',
        }}
      >
        <Sparkles size={18} />
        <span className="text-sm font-medium">Analista IA</span>
        {messages.length > 0 && (
          <span className="w-5 h-5 bg-white text-[10px] font-bold rounded-full flex items-center justify-center"
            style={{ color: '#0066CC' }}>
            {messages.filter(m => m.role === 'assistant').length}
          </span>
        )}
      </button>,
      document.body
    )
  }

  return createPortal(
    <div
      className="fixed bottom-6 right-6 z-[9999] flex flex-col overflow-hidden"
      style={{
        width: 400,
        height: 520,
        maxHeight: 'calc(100vh - 120px)',
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 16,
        fontFamily: 'Inter, sans-serif',
        boxShadow: '0 8px 40px rgba(0, 0, 0, 0.15)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)', background: 'linear-gradient(135deg, #0066CC 0%, #0052A3 100%)' }}
      >
        <div className="flex items-center gap-2">
          <Sparkles size={15} className="text-white" />
          <span className="text-sm font-semibold text-white">Analista IA</span>
          {context?.activeTab && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-pill bg-white/20 text-white font-medium">
              {context.activeTab}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {messages.length > 0 && (
            <button onClick={clearHistory} className="p-1 rounded hover:bg-white/20 transition-colors" title="Limpiar">
              <Trash2 size={12} className="text-white/70" />
            </button>
          )}
          <button onClick={() => setMinimized(true)} className="p-1 rounded hover:bg-white/20 transition-colors" title="Minimizar">
            <Minimize2 size={12} className="text-white/70" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3" style={{ minHeight: 0 }}>
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>
              Preguntame sobre los datos del dashboard
            </p>
            <div className="space-y-1.5">
              {suggestions.map(({ icon: Icon, text }, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(text)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-xs transition-colors hover:opacity-80"
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-light)',
                  }}
                >
                  <Icon size={13} className="text-primary flex-shrink-0" />
                  <span>{text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[90%] rounded-xl px-3 py-2 text-xs ${
                msg.role === 'user' ? 'bg-primary text-white rounded-br-sm' : 'rounded-bl-sm'
              }`}
              style={msg.role === 'assistant' ? {
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-light)',
              } : {}}
            >
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

              {msg.result?.data?.length && msg.result.columns.length >= 2 ? (
                <div className="mt-2 rounded-lg overflow-hidden" style={{ border: '1px solid var(--border-light)' }}>
                  <div className="p-2" style={{ backgroundColor: 'var(--bg-card)' }}>
                    <ChartWidget
                      data={msg.result.data}
                      columns={msg.result.columns}
                      chartType={(msg.result.chart_type || 'bar') as ChartType}
                      height={160}
                    />
                  </div>
                  <div className="flex items-center gap-1 px-2 py-1.5" style={{ borderTop: '1px solid var(--border-light)', backgroundColor: 'var(--bg-surface)' }}>
                    <button
                      onClick={() => handleSaveAsQuery(msg)}
                      className="flex items-center gap-1 text-[10px] px-2 py-1 rounded text-primary font-medium hover:bg-primary/10 transition-colors"
                    >
                      <ExternalLink size={10} /> Abrir en consultas
                    </button>
                    <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                      {msg.result.data.length} filas
                    </span>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs"
              style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-muted)', border: '1px solid var(--border-light)' }}>
              <Loader2 size={12} className="animate-spin" />
              <span>Analizando datos...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-3 py-2.5" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="input flex-1 text-xs"
            placeholder="Pregunta sobre los datos..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button
            className="btn-primary px-3 py-1.5 text-xs flex items-center gap-1"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            <Send size={13} />
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
