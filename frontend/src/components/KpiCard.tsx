import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  icon?: LucideIcon
  color?: string
  delta?: number
}

export default function KpiCard({ label, value, icon: Icon, color = '#0066CC', delta }: Props) {
  const IconComp = Icon || Activity
  return (
    <div className="card p-4 flex items-start gap-3 hover:shadow-card-hover transition-shadow">
      <div
        className="w-10 h-10 rounded-btn flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: `${color}15` }}
      >
        <IconComp size={20} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium uppercase tracking-wider text-text-muted mb-1">
          {label}
        </p>
        <p className="text-2xl font-semibold text-text-dark leading-none">
          {typeof value === 'number' ? value.toLocaleString('es-CO') : value}
        </p>
        {delta !== undefined && (
          <div className={`flex items-center gap-1 mt-1 text-xs font-medium ${
            delta >= 0 ? 'text-green-600' : 'text-red-500'
          }`}>
            {delta >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  )
}
