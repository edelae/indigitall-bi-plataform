import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  MessageSquare, LayoutGrid, Database, Search, Plus,
  TrendingUp, Users, AlertTriangle, Zap, Clock,
} from 'lucide-react'
import KpiCard from '../components/KpiCard'
import ChartWidget from '../components/ChartWidget'
import { fetchAnalytics } from '../api/client'

interface HomeStats {
  total_messages: number
  total_conversations: number
  unique_contacts: number
  active_agents: number
  fallback_rate: number
  total_queries: number
  total_dashboards: number
  recent_queries: any[]
  recent_dashboards: any[]
  trend_30d: Record<string, any>[]
}

export default function Home() {
  const [stats, setStats] = useState<HomeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    fetchAnalytics<HomeStats>('home/stats')
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(timer)
  }, [])

  const dateStr = now.toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  const timeStr = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <img src="/indigitall_logo.webp" alt="inDigitall" className="h-10" />
          <div>
            <h1 className="text-2xl font-bold text-text-dark">inDigitall Analytics</h1>
            <p className="text-text-muted text-sm capitalize">{dateStr} — {timeStr}</p>
          </div>
        </div>
        <span className="text-xs bg-[#0066CC]/10 text-[#0066CC] font-medium px-3 py-1 rounded-full">
          Visionamos PROD
        </span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 mb-6">
        <div className="card p-1">
          <KpiCard
            label="Mensajes"
            value={loading ? '...' : (stats?.total_messages ?? 0).toLocaleString('es-CO')}
            icon={MessageSquare}
            color="#0066CC"
          />
        </div>
        <div className="card p-1">
          <KpiCard
            label="Conversaciones"
            value={loading ? '...' : (stats?.total_conversations ?? 0).toLocaleString('es-CO')}
            icon={TrendingUp}
            color="#00A86B"
          />
        </div>
        <div className="card p-1">
          <KpiCard
            label="Contactos"
            value={loading ? '...' : (stats?.unique_contacts ?? 0).toLocaleString('es-CO')}
            icon={Users}
            color="#0099FF"
          />
        </div>
        <div className="card p-1">
          <KpiCard
            label="Tableros"
            value={loading ? '...' : (stats?.total_dashboards ?? 0)}
            icon={LayoutGrid}
            color="#005299"
          />
        </div>
        <div className="card p-1">
          <KpiCard
            label="Consultas"
            value={loading ? '...' : (stats?.total_queries ?? 0)}
            icon={Search}
            color="#33BB88"
          />
        </div>
        <div className="card p-1">
          <KpiCard
            label="Fallback Rate"
            value={loading ? '...' : `${(stats?.fallback_rate ?? 0).toFixed(1)}%`}
            icon={AlertTriangle}
            color={stats && stats.fallback_rate > 15 ? '#EF4444' : '#00A86B'}
          />
        </div>
      </div>

      {/* Trend + Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 card p-4">
          <h2 className="text-sm font-semibold text-text-dark mb-3">Actividad — Ultimos 30 Dias</h2>
          <div className="h-[240px]">
            {stats?.trend_30d?.length ? (
              <ChartWidget
                data={stats.trend_30d}
                columns={['date', 'count']}
                chartType="area"
                fillContainer
              />
            ) : (
              <div className="flex items-center justify-center h-full text-text-muted text-sm">
                {loading ? 'Cargando...' : 'Sin datos de tendencia'}
              </div>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="text-sm font-semibold text-text-dark mb-3">Dashboards Recientes</h2>
          {stats?.recent_dashboards?.length ? (
            <div className="space-y-2">
              {stats.recent_dashboards.map((d: any) => (
                <Link
                  key={d.id}
                  to={`/tableros/saved/${d.id}`}
                  className="flex items-center gap-2 p-2 rounded hover:bg-surface transition-colors no-underline"
                >
                  <LayoutGrid size={14} className="text-primary flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-dark truncate">{d.name}</p>
                    <p className="text-[11px] text-text-light">{d.widget_count ?? d.layout?.length ?? 0} widgets</p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-[200px] text-text-muted text-sm">
              <LayoutGrid size={24} className="mb-2 text-text-light" />
              {loading ? 'Cargando...' : 'Sin dashboards'}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <h2 className="text-lg font-semibold mb-4">Acciones Rapidas</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link to="/consultas/nueva" className="card p-5 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center mb-2 group-hover:bg-primary/20 transition-colors">
            <MessageSquare size={20} className="text-primary" />
          </div>
          <h3 className="text-sm font-semibold text-text-dark mb-0.5">Nueva Consulta IA</h3>
          <p className="text-xs text-text-muted">Pregunta en lenguaje natural</p>
        </Link>

        <Link to="/tableros/nuevo" className="card p-5 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-10 h-10 bg-secondary/10 rounded-lg flex items-center justify-center mb-2 group-hover:bg-secondary/20 transition-colors">
            <Plus size={20} className="text-secondary" />
          </div>
          <h3 className="text-sm font-semibold text-text-dark mb-0.5">Nuevo Tablero</h3>
          <p className="text-xs text-text-muted">Dashboard personalizado</p>
        </Link>

        <Link to="/datos" className="card p-5 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-2 group-hover:bg-purple-200 transition-colors">
            <Database size={20} className="text-purple-600" />
          </div>
          <h3 className="text-sm font-semibold text-text-dark mb-0.5">Explorar Datos</h3>
          <p className="text-xs text-text-muted">Tablas y esquemas</p>
        </Link>

        <Link to="/tableros/visionamos" className="card p-5 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-10 h-10 bg-[#0066CC]/10 rounded-lg flex items-center justify-center mb-2 group-hover:bg-[#0066CC]/20 transition-colors">
            <Zap size={20} className="text-[#0066CC]" />
          </div>
          <h3 className="text-sm font-semibold text-text-dark mb-0.5">Dashboard Visionamos</h3>
          <p className="text-xs text-text-muted">Datos en tiempo real</p>
        </Link>
      </div>
    </div>
  )
}
