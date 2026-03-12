import { X, Palette, Type, RulerIcon, BarChart3, Columns3, Gauge, Code } from 'lucide-react'
import type { ChartType, QueryResult } from '../types'
import { COLOR_PALETTES, FONT_FAMILIES } from '../types'
import SqlVariables from './SqlVariables'

export interface ChartConfig {
  chartType: ChartType
  colorPalette?: string
  xLabel?: string
  yLabel?: string
  showLegend?: boolean
  fontFamily?: string
  axisFontSize?: number
  legendFontSize?: number
  xColumn?: string
  yColumns?: string[]
  groupByColumn?: string
  kpiStyle?: 'minimal' | 'accent' | 'progress'
  kpiColor?: string
  kpiMaxValue?: number
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
  { value: 'kpi', label: 'Tarjeta KPI' },
  { value: 'table', label: 'Tabla' },
]

interface Props {
  config: ChartConfig
  onChange: (config: ChartConfig) => void
  onClose: () => void
  availableColumns?: string[]
  sql?: string
  lastResult?: QueryResult | null
  onResultUpdate?: (result: QueryResult) => void
}

export default function ChartCustomizer({ config, onChange, onClose, availableColumns = [], sql, lastResult, onResultUpdate }: Props) {
  const update = <K extends keyof ChartConfig>(key: K, value: ChartConfig[K]) => {
    onChange({ ...config, [key]: value })
  }

  const toggleYColumn = (col: string) => {
    const current = config.yColumns || availableColumns.slice(1)
    const next = current.includes(col)
      ? current.filter(c => c !== col)
      : [...current, col]
    if (next.length > 0) update('yColumns', next)
  }

  const xCol = config.xColumn || availableColumns[0]
  const groupCol = config.groupByColumn
  const selectableForY = availableColumns.filter(c => c !== xCol && c !== groupCol)
  const activeYCols = config.yColumns || availableColumns.slice(1)

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
        {/* SQL Variables — interactive SQL modification */}
        {sql && lastResult && onResultUpdate && (
          <section>
            <div className="flex items-center gap-1.5 mb-2">
              <Code size={12} className="text-primary" />
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                Variables SQL
              </p>
            </div>
            <SqlVariables sql={sql} lastResult={lastResult} onResultUpdate={onResultUpdate} />
          </section>
        )}

        {/* Column Assignment (Power BI-style) */}
        {availableColumns.length >= 2 && (
          <section>
            <div className="flex items-center gap-1.5 mb-2">
              <Columns3 size={12} className="text-primary" />
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                Asignacion de columnas
              </p>
            </div>

            {/* X Axis */}
            <label className="text-[10px] mb-0.5 block font-medium" style={{ color: 'var(--text-muted)' }}>Eje X</label>
            <select className="input text-xs mb-2"
              value={xCol}
              onChange={e => {
                const newX = e.target.value
                const newY = (config.yColumns || availableColumns.slice(1)).filter(c => c !== newX)
                onChange({ ...config, xColumn: newX, yColumns: newY.length ? newY : availableColumns.filter(c => c !== newX && c !== groupCol).slice(0, 1) })
              }}>
              {availableColumns.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, x => x.toUpperCase())}</option>)}
            </select>

            {/* Y Values */}
            <label className="text-[10px] mb-0.5 block font-medium" style={{ color: 'var(--text-muted)' }}>Valores (Y)</label>
            <div className="max-h-28 overflow-y-auto rounded-btn mb-2 p-1" style={{ border: '1px solid var(--border-light)' }}>
              {selectableForY.map(col => (
                <label key={col} className="flex items-center gap-1.5 py-0.5 px-1 text-[11px] cursor-pointer hover:bg-surface rounded"
                  style={{ color: 'var(--text-primary)' }}>
                  <input type="checkbox" className="rounded"
                    checked={activeYCols.includes(col)}
                    onChange={() => toggleYColumn(col)} />
                  {col.replace(/_/g, ' ').replace(/\b\w/g, x => x.toUpperCase())}
                </label>
              ))}
            </div>

            {/* Legend / Group by */}
            <label className="text-[10px] mb-0.5 block font-medium" style={{ color: 'var(--text-muted)' }}>Leyenda / Agrupar por</label>
            <select className="input text-xs mb-1"
              value={groupCol || ''}
              onChange={e => {
                const newGroup = e.target.value || undefined
                const newY = newGroup
                  ? availableColumns.filter(c => c !== xCol && c !== newGroup).slice(0, 1)
                  : config.yColumns
                onChange({ ...config, groupByColumn: newGroup, yColumns: newY })
              }}>
              <option value="">Ninguna</option>
              {availableColumns.filter(c => c !== xCol).map(c => (
                <option key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, x => x.toUpperCase())}</option>
              ))}
            </select>
            {groupCol && (
              <p className="text-[9px] mb-1" style={{ color: 'var(--text-light)' }}>
                Cada valor unico de "{groupCol}" sera una serie en la leyenda
              </p>
            )}
          </section>
        )}

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

        {/* KPI Style (only when chart type is kpi) */}
        {config.chartType === 'kpi' && (
          <section>
            <div className="flex items-center gap-1.5 mb-2">
              <Gauge size={12} className="text-primary" />
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                Estilo de tarjeta
              </p>
            </div>
            <div className="grid grid-cols-3 gap-1 mb-3">
              {([['accent', 'Con icono'], ['minimal', 'Minimal'], ['progress', 'Progreso']] as const).map(([val, label]) => (
                <button key={val}
                  onClick={() => update('kpiStyle', val)}
                  className={`px-1.5 py-1.5 rounded-btn text-[10px] text-center transition-colors ${
                    (config.kpiStyle || 'accent') === val
                      ? 'bg-primary text-white'
                      : 'text-text-muted hover:bg-surface'
                  }`}
                  style={(config.kpiStyle || 'accent') !== val ? { backgroundColor: 'var(--bg-surface)' } : {}}>
                  {label}
                </button>
              ))}
            </div>

            <label className="text-[10px] mb-0.5 block font-medium" style={{ color: 'var(--text-muted)' }}>Color</label>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {['#1E88E5', '#76C043', '#9C27B0', '#FF5722', '#FFC107', '#EF4444', '#1565C0', '#A0A3BD'].map(c => (
                <button key={c}
                  onClick={() => update('kpiColor', c)}
                  className={`w-6 h-6 rounded-full transition-all ${
                    (config.kpiColor || '#1E88E5') === c ? 'ring-2 ring-offset-1 ring-primary scale-110' : 'hover:scale-105'
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>

            {(config.kpiStyle || 'accent') === 'progress' && (
              <>
                <label className="text-[10px] mb-0.5 block font-medium" style={{ color: 'var(--text-muted)' }}>Valor maximo (meta)</label>
                <input className="input text-xs"
                  type="number" min="1"
                  placeholder="Ej: 1000"
                  value={config.kpiMaxValue || ''}
                  onChange={e => update('kpiMaxValue', parseInt(e.target.value) || undefined)} />
              </>
            )}
          </section>
        )}

        {/* Color palette */}
        {config.chartType !== 'kpi' && <section>
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
        </section>}

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
