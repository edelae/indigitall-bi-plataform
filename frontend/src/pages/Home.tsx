import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, LayoutGrid, Database, Search, Plus, TrendingUp } from 'lucide-react'
import KpiCard from '../components/KpiCard'
import { listQueries, listDashboards } from '../api/client'

export default function Home() {
  const [queryCount, setQueryCount] = useState(0)
  const [dashCount, setDashCount] = useState(0)

  useEffect(() => {
    listQueries({ limit: 1 }).then(r => setQueryCount(r.total)).catch(() => {})
    listDashboards({ limit: 1 }).then(r => setDashCount(r.total)).catch(() => {})
  }, [])

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-dark mb-1">
          Bienvenido a inDigitall Analytics
        </h1>
        <p className="text-text-muted text-sm">
          Plataforma de Business Intelligence con asistente IA
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Consultas Guardadas"
          value={queryCount}
          icon={Search}
          color="#1E88E5"
        />
        <KpiCard
          label="Tableros Creados"
          value={dashCount}
          icon={LayoutGrid}
          color="#76C043"
        />
        <KpiCard
          label="Canal Principal"
          value="WhatsApp"
          icon={MessageSquare}
          color="#42A5F5"
        />
        <KpiCard
          label="Estado"
          value="Activo"
          icon={TrendingUp}
          color="#76C043"
        />
      </div>

      {/* Quick Actions */}
      <h2 className="text-lg font-semibold mb-4">Acciones Rapidas</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/consultas/nueva" className="card p-6 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-12 h-12 bg-primary/10 rounded-card flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
            <MessageSquare size={24} className="text-primary" />
          </div>
          <h3 className="text-base font-semibold text-text-dark mb-1">Nueva Consulta IA</h3>
          <p className="text-sm text-text-muted">
            Pregunta en lenguaje natural y obtiene graficas y resultados al instante
          </p>
        </Link>

        <Link to="/tableros/nuevo" className="card p-6 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-12 h-12 bg-secondary/10 rounded-card flex items-center justify-center mb-3 group-hover:bg-secondary/20 transition-colors">
            <Plus size={24} className="text-secondary" />
          </div>
          <h3 className="text-base font-semibold text-text-dark mb-1">Nuevo Tablero</h3>
          <p className="text-sm text-text-muted">
            Crea un dashboard personalizado con drag-and-drop desde tus consultas
          </p>
        </Link>

        <Link to="/datos" className="card p-6 hover:shadow-card-hover transition-shadow no-underline group">
          <div className="w-12 h-12 bg-purple-100 rounded-card flex items-center justify-center mb-3 group-hover:bg-purple-200 transition-colors">
            <Database size={24} className="text-purple-600" />
          </div>
          <h3 className="text-base font-semibold text-text-dark mb-1">Explorar Datos</h3>
          <p className="text-sm text-text-muted">
            Navega las tablas, columnas y datos disponibles en la base de datos
          </p>
        </Link>
      </div>
    </div>
  )
}
