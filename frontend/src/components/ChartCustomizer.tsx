import { X, Palette, Type, RulerIcon, BarChart3 } from 'lucide-react'
import type { ChartType } from '../types'
import { COLOR_PALETTES, FONT_FAMILIES } from '../types'

export interface ChartConfig {
  chartType: ChartType
  colorPalette?: string
  xLabel?: string
  yLabel?: string
  showLegend?: boolean
  fontFamily?: string
  axisFontSize?: number
  legendFontSize?: number
}

const CHART_OPTIONS: { value: ChartType; label: string }[] = [
  { value: 'bar', label: 'Barras' },
  { value: 'bar_horizontal', label: 'Barras H.' },
  { value: 'bar_stacked', label: 'Apiladas' },
  { value: 'line', label: 'Linea' },
  { value: 'pie', label: 'Circular' },
  { value: 'area', label: 'Area' },
  { value: 'area_stacked', label: 'Area Apilada' },
  { value: 'scatter', label: 'Dispersion' },
  { value: 'combo', label: 'Combo' },
  { value: 'funnel', label: 'Embudo' },
  { value: 'treemap', label: 'Treemap' },
  { value: 'heatmap', label: 'Heatmap' },
  { value: 'gauge', label: 'Gauge' },
]

interface Props {
  config: ChartConfig
  onChange: (config: ChartConfig) => void
  onClose: () => void
}

export default function ChartCustomizer({ config, onChange, onClose }: Props) {
  const update = <K extends keyof ChartConfig>(key: K, value: ChartConfig[K]) => {
    onChange({ ...config, [key]: value })
  }

  return (
    <div className="w-[280px] flex flex-col border-l border-border-light h-full overflow-y-auto"
      style={{ backgroundColor: 'var(--bg-card)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border-light">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          Personalizar
        </span>
        <button onClick={onClose} className="btn-icon p-1">
          <X size={14} />
        </button>
      </div>

      <div className="p-3 space-y-4">
        {/* Chart type */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Tipo de grafica
            </p>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {CHART_OPTIONS.map(opt => (
              <button key={opt.value}
                onClick={() => update('chartType', opt.value)}
                className={`px-1.5 py-1 rounded-btn text-[10px] text-center transition-colors ${
                  config.chartType === opt.value
                    ? 'bg-primary text-white'
                    : 'text-text-muted hover:bg-surface'
                }`}
                style={config.chartType !== opt.value ? { backgroundColor: 'var(--bg-surface)' } : {}}>
                {opt.label}
              </button>
            ))}
          </div>
        </section>

        {/* Color palette */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <Palette size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Paleta de colores
            </p>
          </div>
          <div className="space-y-0.5">
            <button
              onClick={() => update('colorPalette', undefined)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-btn text-[11px] transition-colors ${
                !config.colorPalette ? 'bg-primary/10 font-semibold' : 'hover:bg-surface'
              }`}>
              <span style={{ color: 'var(--text-primary)' }}>Por defecto</span>
            </button>
            {Object.entries(COLOR_PALETTES).map(([key, pal]) => (
              <button key={key}
                onClick={() => update('colorPalette', key)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-btn text-[11px] transition-colors ${
                  config.colorPalette === key ? 'bg-primary/10 font-semibold' : 'hover:bg-surface'
                }`}>
                <div className="flex gap-0.5">
                  {pal.colors.slice(0, 5).map((c, ci) => (
                    <div key={ci} className="w-3 h-3 rounded-full" style={{ backgroundColor: c }} />
                  ))}
                </div>
                <span style={{ color: 'var(--text-primary)' }}>{pal.name}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Axis labels */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <RulerIcon size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Etiquetas de ejes
            </p>
          </div>
          <input className="input text-xs mb-1.5"
            placeholder="Nombre eje X"
            value={config.xLabel || ''}
            onChange={e => update('xLabel', e.target.value || undefined)} />
          <input className="input text-xs"
            placeholder="Nombre eje Y"
            value={config.yLabel || ''}
            onChange={e => update('yLabel', e.target.value || undefined)} />
          <label className="flex items-center gap-2 mt-2 text-xs cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
            <input type="checkbox" className="rounded"
              checked={config.showLegend !== false}
              onChange={e => update('showLegend', e.target.checked)} />
            Mostrar leyenda
          </label>
        </section>

        {/* Typography */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <Type size={12} className="text-primary" />
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Tipografia
            </p>
          </div>
          <select className="input text-xs mb-1.5"
            value={config.fontFamily || ''}
            onChange={e => update('fontFamily', e.target.value || undefined)}>
            <option value="">Por defecto (Inter)</option>
            {FONT_FAMILIES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
          <div className="flex gap-1.5">
            <div className="flex-1">
              <label className="text-[10px] mb-0.5 block" style={{ color: 'var(--text-muted)' }}>Ejes px</label>
              <input className="input text-xs" type="number" min="8" max="24"
                placeholder="12"
                value={config.axisFontSize || ''}
                onChange={e => update('axisFontSize', parseInt(e.target.value) || undefined)} />
            </div>
            <div className="flex-1">
              <label className="text-[10px] mb-0.5 block" style={{ color: 'var(--text-muted)' }}>Leyenda px</label>
              <input className="input text-xs" type="number" min="8" max="24"
                placeholder="11"
                value={config.legendFontSize || ''}
                onChange={e => update('legendFontSize', parseInt(e.target.value) || undefined)} />
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
