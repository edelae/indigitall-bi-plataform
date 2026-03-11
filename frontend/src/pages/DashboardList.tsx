import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LayoutGrid, Plus, Search, Star, Archive,
  Clock, Loader2, Pencil, Eye, Zap,
  MessageSquare, Headphones, Send, Shield,
  Bot, ThumbsUp,
} from 'lucide-react'
import { listDashboards, toggleDashboardFavorite, archiveDashboard } from '../api/client'
import type { Dashboard, DashboardWidget } from '../types'
import { CHART_COLORS } from '../types'

// Simplified SVG representation of a chart type for the mini preview
function MiniChartSvg({ type, color }: { type: string; color: string }) {
  if (type === 'kpi' || type === 'text_card') {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center gap-0.5">
        <div className="h-1 rounded-full" style={{ width: '40%', backgroundColor: color }} />
        <div className="h-0.5 bg-gray-200 rounded-full" style={{ width: '60%' }} />
      </div>
    )
  }
  if (type === 'title') {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="h-1 bg-gray-300 rounded-full" style={{ width: '70%' }} />
      </div>
    )
  }
  return (
    <svg viewBox="0 0 40 24" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
      {type === 'line' || type === 'area' || type === 'area_stacked' ? (
        <>
          {type.includes('area') && (
            <polygon points="4,16 12,10 20,13 28,6 36,9 36,22 4,22" fill={color} fillOpacity="0.15" />
          )}
          <polyline points="4,16 12,10 20,13 28,6 36,9" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </>
      ) : type === 'pie' ? (
        <g transform="translate(20,12)">
          <circle r="10" fill={color} opacity="0.15" />
          <path d="M0,-10 A10,10 0 0,1 8.66,5 L0,0 Z" fill={color} />
          <path d="M8.66,5 A10,10 0 0,1 -5,8.66 L0,0 Z" fill={color} opacity="0.6" />
        </g>
      ) : type === 'scatter' ? (
        <>
          <circle cx="8" cy="16" r="2" fill={color} opacity="0.6" />
          <circle cx="16" cy="8" r="2" fill={color} />
          <circle cx="24" cy="14" r="2" fill={color} opacity="0.7" />
          <circle cx="32" cy="6" r="2" fill={color} opacity="0.8" />
        </>
      ) : type === 'table' ? (
        <>
          <rect x="3" y="2" width="34" height="3" rx="0.5" fill={color} opacity="0.25" />
          <rect x="3" y="7" width="34" height="2" rx="0.5" fill="#E5E7EB" />
          <rect x="3" y="11" width="34" height="2" rx="0.5" fill="#E5E7EB" />
          <rect x="3" y="15" width="34" height="2" rx="0.5" fill="#E5E7EB" />
          <rect x="3" y="19" width="34" height="2" rx="0.5" fill="#E5E7EB" />
        </>
      ) : type === 'heatmap' ? (
        <>
          {[0,1,2].map(r => [0,1,2,3].map(c => (
            <rect key={`${r}-${c}`} x={3 + c * 9} y={2 + r * 7} width="8" height="6" rx="1"
              fill={color} opacity={0.2 + Math.random() * 0.6} />
          )))}
        </>
      ) : type === 'funnel' ? (
        <>
          <rect x="4" y="2" width="32" height="5" rx="1" fill={color} />
          <rect x="8" y="9" width="24" height="5" rx="1" fill={color} opacity="0.7" />
          <rect x="12" y="16" width="16" height="5" rx="1" fill={color} opacity="0.4" />
        </>
      ) : (
        /* Default: bar chart (also handles bar_horizontal, bar_stacked, histogram, combo) */
        <>
          <rect x="3" y="14" width="5" height="8" rx="1" fill={color} opacity="0.6" />
          <rect x="10" y="8" width="5" height="14" rx="1" fill={color} opacity="0.8" />
          <rect x="17" y="11" width="5" height="11" rx="1" fill={color} opacity="0.65" />
          <rect x="24" y="4" width="5" height="18" rx="1" fill={color} />
          <rect x="31" y="9" width="5" height="13" rx="1" fill={color} opacity="0.7" />
        </>
      )}
    </svg>
  )
}

// Proportional mini layout preview of the dashboard
function MiniDashboardPreview({ widgets }: { widgets: DashboardWidget[] }) {
  if (!widgets?.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <LayoutGrid size={32} className="text-text-light" />
      </div>
    )
  }

  const maxY = Math.max(...widgets.map(w => (w.grid_y ?? 0) + (w.grid_h ?? 4)), 1)

  return (
    <div className="relative w-full h-full p-1">
      {widgets.slice(0, 12).map((w, i) => {
        const gx = w.grid_x ?? (i % 2) * 6
        const gy = w.grid_y ?? Math.floor(i / 2) * 4
        const gw = w.grid_w ?? w.width ?? 6
        const gh = w.grid_h ?? 4
        const type = w.chart_type || w.type || 'bar'
        const color = CHART_COLORS[i % CHART_COLORS.length]

        return (
          <div
            key={i}
            className="absolute rounded-sm bg-white overflow-hidden"
            style={{
              left: `${(gx / 12) * 100}%`,
              top: `${(gy / maxY) * 100}%`,
              width: `${(gw / 12) * 100}%`,
              height: `${(gh / maxY) * 100}%`,
              padding: '2px',
              boxShadow: '0 0 0 0.5px rgba(0,0,0,0.1)',
            }}
          >
            <MiniChartSvg type={type} color={color} />
          </div>
        )
      })}
    </div>
  )
}

export default function DashboardList() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const result = await listDashboards({ limit: 50, search: search || undefined })
      setDashboards(result.dashboards)
      setTotal(result.total)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search]) // eslint-disable-line

  const handleFavorite = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    await toggleDashboardFavorite(id)
    load()
  }

  const handleArchive = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (confirm('Archivar este tablero?')) {
      await archiveDashboard(id)
      load()
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-dark">Tableros</h1>
          <p className="text-sm text-text-muted">{total} tableros creados</p>
        </div>
        <Link to="/tableros/nuevo" className="btn-primary flex items-center gap-1.5 text-sm no-underline">
          <Plus size={16} /> Nuevo Tablero
        </Link>
      </div>

      <div className="relative max-w-sm mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-light" />
        <input
          className="input pl-9"
          placeholder="Buscar tableros..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Visionamos — predefined live dashboard */}
          <div
            onClick={() => navigate('/tableros/visionamos')}
            className="card overflow-hidden cursor-pointer hover:shadow-card-hover transition-all relative"
          >
            <div className="h-40 relative overflow-hidden bg-gradient-to-br from-[#0066CC] to-[#003D73] flex items-center justify-center">
              <div className="absolute inset-0 opacity-10">
                <svg viewBox="0 0 200 120" className="w-full h-full">
                  <rect x="10" y="10" width="40" height="100" rx="4" fill="white" />
                  <rect x="60" y="30" width="40" height="80" rx="4" fill="white" />
                  <rect x="110" y="20" width="40" height="90" rx="4" fill="white" />
                  <rect x="160" y="50" width="30" height="60" rx="4" fill="white" />
                </svg>
              </div>
              <div className="text-center relative z-10">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Zap size={20} className="text-white" />
                  <span className="text-white font-bold text-lg">Visionamos</span>
                </div>
                <div className="flex items-center justify-center gap-3 mt-2">
                  {[MessageSquare, Headphones, Send, Shield].map((Icon, i) => (
                    <div key={i} className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center">
                      <Icon size={13} className="text-white" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="p-4">
              <div className="flex items-start justify-between mb-1">
                <h3 className="font-semibold text-sm text-text-dark">Dashboard Visionamos</h3>
                <span className="badge badge-primary text-[10px]">En vivo</span>
              </div>
              <p className="text-xs text-text-muted mb-2">WhatsApp, Bot, Contact Center, SMS y Control de Toques con datos en tiempo real</p>
              <div className="flex items-center gap-2 text-[11px] text-text-light">
                <span className="badge badge-info">5 tabs</span>
                <span className="badge badge-success">Datos reales</span>
              </div>
            </div>
          </div>

          {/* WhatsApp NPS & Bot — predefined analytics dashboard */}
          <div
            onClick={() => navigate('/tableros/whatsapp-nps')}
            className="card overflow-hidden cursor-pointer hover:shadow-card-hover transition-all relative"
          >
            <div className="h-40 relative overflow-hidden bg-gradient-to-br from-[#003D73] to-[#0066CC] flex items-center justify-center">
              <div className="absolute inset-0 opacity-10">
                <svg viewBox="0 0 200 120" className="w-full h-full">
                  <polyline points="10,90 50,40 90,60 130,20 170,50" fill="none" stroke="white" strokeWidth="4" />
                  <rect x="20" y="70" width="20" height="40" rx="3" fill="white" />
                  <rect x="60" y="50" width="20" height="60" rx="3" fill="white" />
                  <rect x="100" y="30" width="20" height="80" rx="3" fill="white" />
                  <rect x="140" y="60" width="20" height="50" rx="3" fill="white" />
                </svg>
              </div>
              <div className="text-center relative z-10">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <MessageSquare size={20} className="text-white" />
                  <span className="text-white font-bold text-lg">NPS & Bot</span>
                </div>
                <div className="flex items-center justify-center gap-3 mt-2">
                  {[ThumbsUp, Bot, Star, MessageSquare].map((Icon, i) => (
                    <div key={i} className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center">
                      <Icon size={13} className="text-white" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="p-4">
              <div className="flex items-start justify-between mb-1">
                <h3 className="font-semibold text-sm text-text-dark">WhatsApp Analytics — NPS & Bot</h3>
                <span className="badge badge-primary text-[10px]">En vivo</span>
              </div>
              <p className="text-xs text-text-muted mb-2">Encuestas de satisfaccion NPS por canal y analisis de fallbacks del bot</p>
              <div className="flex items-center gap-2 text-[11px] text-text-light">
                <span className="badge badge-info">2 tabs</span>
                <span className="badge badge-success">NPS + Fallbacks</span>
              </div>
            </div>
          </div>

          {dashboards.map(d => {
            const widgetCount = d.layout?.length || 0
            const isHovered = hoveredId === d.id
            return (
              <div
                key={d.id}
                onClick={() => navigate(`/tableros/saved/${d.id}`)}
                onMouseEnter={() => setHoveredId(d.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="card overflow-hidden cursor-pointer hover:shadow-card-hover transition-all relative"
              >
                {/* Thumbnail area — proportional mini preview of dashboard layout */}
                <div className="bg-surface h-40 relative overflow-hidden">
                  <MiniDashboardPreview widgets={d.layout || []} />

                  {/* Hover overlay with actions */}
                  {isHovered && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-3 animate-fade-in">
                      <button
                        onClick={e => { e.stopPropagation(); navigate(`/tableros/saved/${d.id}`) }}
                        className="bg-white text-text-dark px-4 py-2 rounded-btn text-sm font-medium flex items-center gap-1.5 hover:bg-gray-50 transition-colors"
                      >
                        <Eye size={14} /> Ver
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); navigate(`/tableros/nuevo?edit=${d.id}`) }}
                        className="bg-primary text-white px-4 py-2 rounded-btn text-sm font-medium flex items-center gap-1.5 hover:bg-primary-dark transition-colors"
                      >
                        <Pencil size={14} /> Editar
                      </button>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-semibold text-sm text-text-dark line-clamp-1">{d.name}</h3>
                    <div className="flex gap-1 flex-shrink-0 ml-2">
                      <button onClick={e => handleFavorite(e, d.id)} className="btn-icon p-0.5">
                        <Star size={13} fill={d.is_favorite ? '#FFC107' : 'none'} className={d.is_favorite ? 'text-yellow-500' : ''} />
                      </button>
                      <button onClick={e => handleArchive(e, d.id)} className="btn-icon p-0.5">
                        <Archive size={13} />
                      </button>
                    </div>
                  </div>
                  {d.description && (
                    <p className="text-xs text-text-muted line-clamp-2 mb-2">{d.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-[11px] text-text-light">
                    <span className="flex items-center gap-1">
                      <Clock size={11} />
                      {d.updated_at ? new Date(d.updated_at).toLocaleDateString('es-CO') : ''}
                    </span>
                    <span className="badge badge-info">{widgetCount} widgets</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
