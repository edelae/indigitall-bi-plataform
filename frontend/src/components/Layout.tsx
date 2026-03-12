import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, Search, LayoutGrid, Database, Plus, ChevronDown, Sun, Moon } from 'lucide-react'
import { useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'

const NAV_ITEMS = [
  { path: '/', label: 'Inicio', icon: Home },
  { path: '/consultas', label: 'Consultas', icon: Search },
  { path: '/tableros', label: 'Tableros', icon: LayoutGrid },
  { path: '/datos', label: 'Datos', icon: Database },
]

export default function Layout() {
  const location = useLocation()
  const [createOpen, setCreateOpen] = useState(false)
  const { isDark, toggle } = useTheme()

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white dark:bg-gray-900 border-b border-border-light dark:border-gray-800 shadow-sm">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
          {/* Left: Logo */}
          <Link to="/" className="flex items-center gap-2 no-underline">
            <img src="/indigitall_logo.webp" alt="inDigitall" className="h-8" />
            <span className="text-lg font-semibold text-text-dark">Analytics</span>
          </Link>

          {/* Center: Nav links */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
              const isActive = path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(path)
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-btn text-sm font-medium transition-colors no-underline ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-text-muted hover:bg-surface hover:text-text-dark'
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              )
            })}
          </div>

          {/* Right: Theme toggle + Create dropdown */}
          <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            className="p-2 rounded-btn text-text-muted hover:bg-surface dark:hover:bg-gray-800 transition-colors"
            title={isDark ? 'Modo claro' : 'Modo oscuro'}
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className="relative">
            <button
              onClick={() => setCreateOpen(!createOpen)}
              className="btn-primary flex items-center gap-1 text-sm py-1.5 px-3"
            >
              <Plus size={16} />
              Crear
              <ChevronDown size={14} />
            </button>
            {createOpen && (
              <>
                <div className="fixed inset-0" onClick={() => setCreateOpen(false)} />
                <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-btn shadow-card-hover border border-border-light dark:border-gray-700 z-50">
                  <Link
                    to="/consultas/nueva"
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-text-dark hover:bg-surface no-underline"
                    onClick={() => setCreateOpen(false)}
                  >
                    <Search size={14} />
                    Nueva Consulta
                  </Link>
                  <Link
                    to="/tableros/nuevo"
                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-text-dark hover:bg-surface no-underline"
                    onClick={() => setCreateOpen(false)}
                  >
                    <LayoutGrid size={14} />
                    Nuevo Tablero
                  </Link>
                </div>
              </>
            )}
          </div>
          </div>
        </div>
      </nav>

      {/* Content — full-width for dashboard builder & view */}
      <main className={`mx-auto py-6 ${
        location.pathname.startsWith('/tableros/saved/') || location.pathname === '/tableros/nuevo'
          ? 'px-4'
          : 'max-w-[1400px] px-6'
      }`}>
        <Outlet />
      </main>
    </div>
  )
}
