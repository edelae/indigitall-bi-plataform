import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'

type KpiStyle = 'minimal' | 'accent' | 'progress'

interface Props {
  label: string
  value: string | number
  icon?: LucideIcon
  color?: string
  delta?: number
  kpiStyle?: KpiStyle
  maxValue?: number
}

export default function KpiCard({ label, value, icon: Icon, color = '#0066CC', delta, kpiStyle = 'accent', maxValue }: Props) {
  const IconComp = Icon || Activity
  const numVal = typeof value === 'number' ? value : parseFloat(String(value).replace(/[,%]/g, ''))
  const displayVal = typeof value === 'number' ? value.toLocaleString('es-CO') : value

  // Minimal: just number + label, clean and compact
  if (kpiStyle === 'minimal') {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-2">
        <p
          className="font-bold text-center leading-none"
          style={{ color, fontSize: 'clamp(1.25rem, 3vw, 2.5rem)' }}
        >
          {displayVal}
        </p>
        <p
          className="text-center uppercase tracking-wider text-[#6B7280] mt-1 font-medium"
          style={{ fontSize: 'clamp(0.55rem, 1.2vw, 0.8rem)' }}
        >
          {label}
        </p>
        {delta !== undefined && (
          <div className={`flex items-center gap-0.5 mt-1 font-medium ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}
            style={{ fontSize: 'clamp(0.5rem, 1vw, 0.75rem)' }}>
            {delta >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
          </div>
        )}
      </div>
    )
  }

  // Progress: with progress bar
  if (kpiStyle === 'progress' && maxValue && !isNaN(numVal)) {
    const pct = Math.min((numVal / maxValue) * 100, 100)
    return (
      <div className="w-full h-full flex flex-col justify-center p-3" style={{ borderLeft: `4px solid ${color}`, borderRadius: 12 }}>
        <p
          className="uppercase tracking-wider text-[#6B7280] font-medium mb-1"
          style={{ fontSize: 'clamp(0.55rem, 1.1vw, 0.75rem)' }}
        >
          {label}
        </p>
        <p
          className="font-bold leading-none mb-2"
          style={{ color, fontSize: 'clamp(1.1rem, 2.5vw, 2rem)' }}
        >
          {displayVal}
        </p>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
        </div>
        <p className="text-[#9CA3AF] mt-0.5" style={{ fontSize: 'clamp(0.45rem, 0.9vw, 0.65rem)' }}>
          {pct.toFixed(0)}% de {maxValue.toLocaleString('es-CO')}
        </p>
      </div>
    )
  }

  // Accent (default): icon + color left border
  return (
    <div
      className="w-full h-full flex items-center gap-3 p-3"
      style={{ borderLeft: `4px solid ${color}`, borderRadius: 12 }}
    >
      <div
        className="flex-shrink-0 rounded-lg flex items-center justify-center"
        style={{
          backgroundColor: `${color}15`,
          width: 'clamp(2rem, 4vw, 3rem)',
          height: 'clamp(2rem, 4vw, 3rem)',
        }}
      >
        <IconComp style={{ color, width: 'clamp(1rem, 2vw, 1.5rem)', height: 'clamp(1rem, 2vw, 1.5rem)' }} />
      </div>
      <div className="flex-1 min-w-0">
        <p
          className="uppercase tracking-wider text-[#6B7280] font-medium leading-tight"
          style={{ fontSize: 'clamp(0.55rem, 1.1vw, 0.75rem)' }}
        >
          {label}
        </p>
        <p
          className="font-bold leading-none mt-0.5"
          style={{ color: '#1F2937', fontSize: 'clamp(1.1rem, 2.5vw, 2rem)' }}
        >
          {displayVal}
        </p>
        {delta !== undefined && (
          <div className={`flex items-center gap-0.5 mt-0.5 font-medium ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}
            style={{ fontSize: 'clamp(0.5rem, 1vw, 0.7rem)' }}>
            {delta >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  )
}
