import { useMemo } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ScatterChart, Scatter,
  ComposedChart, Treemap, FunnelChart, Funnel, LabelList,
} from 'recharts'
import type { ChartType } from '../types'
import { CHART_COLORS } from '../types'

interface Props {
  data: Record<string, any>[]
  columns: string[]
  chartType: ChartType
  height?: number
  colors?: string[]
  xLabel?: string
  yLabel?: string
  showLegend?: boolean
  onClickPoint?: (point: Record<string, any>) => void
  fillContainer?: boolean
  fontFamily?: string
  axisFontSize?: number
  legendFontSize?: number
}

const LABELS: Record<string, string> = {
  // Date/time
  date: 'Fecha', fecha: 'Fecha', created_at: 'Fecha Creación', updated_at: 'Fecha Actualización',
  sent_at: 'Fecha Envío', stats_date: 'Fecha', statsdate: 'Fecha',
  hour: 'Hora', day: 'Día', month: 'Mes', week: 'Semana', year: 'Año',
  day_of_week: 'Día de la Semana', dia_semana: 'Día de la Semana',
  // Counts
  count: 'Cantidad', total: 'Total', messages: 'Mensajes', msg_count: 'Mensajes',
  total_messages: 'Total Mensajes', total_sent: 'Total Enviados',
  total_delivered: 'Total Entregados', total_clicks: 'Total Clicks',
  total_chunks: 'Total Chunks', total_cost: 'Costo Total',
  total_enviados: 'Total Enviados', total_entregados: 'Total Entregados',
  unique_contacts: 'Contactos Únicos', num_contacts_sent: 'Contactos Enviados',
  num_contacts_clicked: 'Contactos con Click',
  // Entities
  name: 'Nombre', value: 'Valor', agent_name: 'Agente', contact_name: 'Contacto',
  contact_id: 'ID Contacto', phone: 'Teléfono', campaign_name: 'Campaña',
  campaign_id: 'ID Campaña',
  // Status/categories
  status: 'Estado', category: 'Categoría', channel: 'Canal', canal: 'Canal',
  type: 'Tipo', direction: 'Dirección', intent: 'Intención',
  // Rates
  rate: 'Tasa', percentage: 'Porcentaje', ctr: 'CTR', delivery_rate: 'Tasa Entrega',
  fallback_rate: 'Tasa Fallback', rejection_rate: 'Tasa Rechazo',
  // Metrics
  cost: 'Costo', clicks: 'Clicks', enviados: 'Enviados', entregados: 'Entregados',
  abiertos: 'Abiertos', conversiones: 'Conversiones',
  avg_handle_time: 'Tiempo Promedio', avg_response_time: 'Tiempo Respuesta',
  first_response_time: 'Primera Respuesta',
}

// Pattern-based label detection
const LABEL_PATTERNS: [RegExp, string][] = [
  [/^total_/, 'Total '],
  [/^avg_/, 'Promedio '],
  [/^num_/, 'N° '],
  [/^is_/, '¿Es '],
  [/^has_/, '¿Tiene '],
  [/_count$/, ' (Cantidad)'],
  [/_rate$/, ' (Tasa)'],
  [/_pct$/, ' (%)'],
  [/_id$/, ' ID'],
]

function getLabel(col: string): string {
  const lower = col.toLowerCase()
  if (LABELS[lower]) return LABELS[lower]
  // Try without common prefixes/suffixes
  const stripped = lower.replace(/^(total|avg|num|max|min)_/, '').replace(/_(count|rate|pct|id)$/, '')
  if (LABELS[stripped]) return LABELS[stripped]
  // Fallback: title-case with underscore replacement
  return col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function ChartWidget({ data, columns, chartType, height = 300, colors, xLabel, yLabel, showLegend = true, onClickPoint, fillContainer, fontFamily, axisFontSize, legendFontSize }: Props) {
  const xKey = columns[0]
  const yKey = columns.length > 1 ? columns[1] : columns[0]
  const yKeys = columns.slice(1)
  const palette = colors || CHART_COLORS
  const chartHeight: number | string = fillContainer ? '100%' : height
  const axisFs = axisFontSize || 12
  const legendFs = legendFontSize || 11
  const ff = fontFamily || 'Inter'

  const processedData = useMemo(() => {
    return data.map(row => {
      const newRow = { ...row }
      for (const col of columns.slice(1)) {
        if (typeof newRow[col] === 'string') {
          const num = parseFloat(newRow[col].replace(/,/g, '').replace(/%/g, ''))
          if (!isNaN(num)) newRow[col] = num
        }
      }
      return newRow
    })
  }, [data, columns])

  const handleClick = (point: any) => {
    if (onClickPoint && point?.activePayload?.[0]) {
      onClickPoint(point.activePayload[0].payload)
    }
  }

  if (chartType === 'table' || chartType === 'kpi' || !data.length || columns.length < 2) {
    return null
  }

  // Auto-generate axis labels from column names if user didn't set custom ones
  const autoXLabel = xLabel || getLabel(xKey)
  const autoYLabel = yLabel || (yKeys.length === 1 ? getLabel(yKeys[0]) : undefined)

  const commonAxisProps = {
    tick: { fontSize: axisFs, fill: '#6E7191', fontFamily: ff },
    axisLine: { stroke: '#E4E4E7' },
    tickLine: false,
    tickFormatter: (value: any) => {
      if (typeof value === 'string' && value.length > 16) return value.slice(0, 14) + '…'
      if (typeof value === 'number' && value >= 1000) return (value / 1000).toFixed(1) + 'K'
      return value
    },
  }

  const xAxisLabel = { value: autoXLabel, position: 'insideBottom' as const, offset: -5, style: { fontSize: axisFs, fill: '#6E7191', fontFamily: ff } }
  const yAxisLabel = autoYLabel ? { value: autoYLabel, angle: -90, position: 'insideLeft' as const, style: { fontSize: axisFs, fill: '#6E7191', fontFamily: ff } } : undefined

  const tooltipStyle = {
    contentStyle: {
      backgroundColor: '#1A1A2E',
      border: 'none',
      borderRadius: 8,
      color: 'white',
      fontSize: 13,
      fontFamily: ff,
    },
    itemStyle: { color: 'white' },
    labelStyle: { color: '#A0A3BD', marginBottom: 4 },
  }

  const legendStyle = { fontSize: legendFs, fontFamily: ff }

  const rotateX = data.length > 6

  // PIE
  if (chartType === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <PieChart>
          <Pie
            data={processedData}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius="38%"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={{ stroke: '#A0A3BD' }}
          >
            {processedData.map((_, i) => (
              <Cell key={i} fill={palette[i % palette.length]} />
            ))}
          </Pie>
          <Tooltip {...tooltipStyle} />
          <Legend wrapperStyle={legendStyle} />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  // LINE
  if (chartType === 'line') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Line key={col} type="monotone" dataKey={col} stroke={palette[i % palette.length]} strokeWidth={2.5} dot={{ fill: palette[i % palette.length], r: 3 }} activeDot={{ r: 5 }} name={getLabel(col)} />
          ))}
          {yKeys.length > 1 && <Legend wrapperStyle={legendStyle} />}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  // AREA
  if (chartType === 'area') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <AreaChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Area type="monotone" dataKey={yKey} stroke={palette[0]} fill={`${palette[0]}1A`} strokeWidth={2} name={getLabel(yKey)} />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // AREA STACKED
  if (chartType === 'area_stacked') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <AreaChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Area key={col} type="monotone" dataKey={col} stackId="1" stroke={palette[i % palette.length]} fill={palette[i % palette.length]} fillOpacity={0.6} name={getLabel(col)} />
          ))}
          <Legend wrapperStyle={legendStyle} />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // HORIZONTAL BAR
  if (chartType === 'bar_horizontal') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={processedData} layout="vertical" onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis type="number" {...commonAxisProps} />
          <YAxis dataKey={xKey} type="category" {...commonAxisProps} width={120} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey={yKey} fill={palette[0]} radius={[0, 4, 4, 0]} name={getLabel(yKey)} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // STACKED BAR
  if (chartType === 'bar_stacked') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Bar key={col} dataKey={col} stackId="stack" fill={palette[i % palette.length]} name={getLabel(col)} />
          ))}
          <Legend wrapperStyle={legendStyle} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // SCATTER
  if (chartType === 'scatter') {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ScatterChart onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} name={getLabel(xKey)} />
          <YAxis dataKey={yKey} {...commonAxisProps} name={getLabel(yKey)} />
          <Tooltip {...tooltipStyle} />
          <Scatter data={processedData} fill={palette[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // COMBO (bar + line)
  if (chartType === 'combo' && yKeys.length >= 2) {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey={yKeys[0]} fill={palette[0]} radius={[4, 4, 0, 0]} name={getLabel(yKeys[0])} />
          <Line type="monotone" dataKey={yKeys[1]} stroke={palette[1]} strokeWidth={2.5} dot={{ fill: palette[1], r: 3 }} name={getLabel(yKeys[1])} />
          <Legend wrapperStyle={legendStyle} />
        </ComposedChart>
      </ResponsiveContainer>
    )
  }

  // FUNNEL
  if (chartType === 'funnel') {
    const funnelData = processedData.map((row, i) => ({
      name: String(row[xKey]),
      value: Number(row[yKey]) || 0,
      fill: palette[i % palette.length],
    }))
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <FunnelChart>
          <Tooltip {...tooltipStyle} />
          <Funnel dataKey="value" data={funnelData} isAnimationActive>
            <LabelList position="center" fill="#fff" stroke="none" fontSize={12} dataKey="name" />
          </Funnel>
        </FunnelChart>
      </ResponsiveContainer>
    )
  }

  // TREEMAP
  if (chartType === 'treemap') {
    const treemapData = processedData.map((row, i) => ({
      name: String(row[xKey]),
      size: Number(row[yKey]) || 0,
      fill: palette[i % palette.length],
    }))
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <Treemap
          data={treemapData}
          dataKey="size"
          nameKey="name"
          stroke="#fff"
          fill={palette[0]}
        >
          <Tooltip {...tooltipStyle} />
        </Treemap>
      </ResponsiveContainer>
    )
  }

  // HEATMAP — horizontal layout: hours (0-23) on X, days (Lun-Dom) on Y
  if (chartType === 'heatmap' && columns.length >= 3) {
    const zKey = columns[2]
    const dayOrder = ['Lunes', 'Martes', 'Miercoles', 'Miércoles', 'Jueves', 'Viernes', 'Sabado', 'Sábado', 'Domingo']
    const dayAbbrev: Record<string, string> = {
      'Lunes': 'Lun', 'Martes': 'Mar', 'Miercoles': 'Mie', 'Miércoles': 'Mié',
      'Jueves': 'Jue', 'Viernes': 'Vie', 'Sabado': 'Sáb', 'Sábado': 'Sáb', 'Domingo': 'Dom',
    }
    const sortAxis = (raw: string[]) => {
      if (raw.some(v => dayOrder.includes(v))) return dayOrder.filter(d => raw.includes(d))
      if (raw.every(v => !isNaN(Number(v)))) return [...raw].sort((a, b) => Number(a) - Number(b))
      return raw
    }

    // Determine which column is days and which is hours
    const rawCol0 = [...new Set(processedData.map(r => String(r[xKey])))]
    const rawCol1 = [...new Set(processedData.map(r => String(r[yKey])))]
    const col0IsDays = rawCol0.some(v => dayOrder.includes(v))
    const col1IsDays = rawCol1.some(v => dayOrder.includes(v))

    // Force: days on Y (rows), hours on X (columns) for horizontal layout
    let dayCol: string, hourCol: string
    if (col0IsDays) { dayCol = xKey; hourCol = yKey }
    else if (col1IsDays) { dayCol = yKey; hourCol = xKey }
    else { dayCol = xKey; hourCol = yKey }

    const days = sortAxis([...new Set(processedData.map(r => String(r[dayCol])))])
    const hours = sortAxis([...new Set(processedData.map(r => String(r[hourCol])))])

    const allZ = processedData.map(r => Number(r[zKey]) || 0)
    const minZ = Math.min(...allZ)
    const maxZ = Math.max(...allZ)
    const rangeZ = maxZ - minZ || 1

    const getColor = (val: number) => {
      const t = (val - minZ) / rangeZ
      if (t < 0.25) return `rgba(0, 102, 204, ${0.08 + t * 0.32})`
      if (t < 0.5) return `rgba(0, 102, 204, ${0.18 + (t - 0.25) * 1.2})`
      if (t < 0.75) return `rgba(0, 82, 163, ${0.55 + (t - 0.5) * 1.2})`
      return `rgba(0, 61, 115, ${0.8 + (t - 0.75) * 0.8})`
    }
    const textColor = (val: number) => ((val - minZ) / rangeZ) > 0.35 ? '#fff' : '#374151'

    return (
      <div style={{ width: '100%', height: fillContainer ? '100%' : height, display: 'flex', flexDirection: 'column' }}>
        {/* CSS Grid heatmap — fully responsive */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: `56px repeat(${hours.length}, 1fr) 20px`,
          gridTemplateRows: `20px repeat(${days.length}, 1fr)`,
          gap: 2,
          flex: 1,
          minHeight: 0,
          fontFamily: ff,
          padding: '0 4px 4px 0',
        }}>
          {/* Top-left corner */}
          <div />
          {/* Hour labels (top) */}
          {hours.map(h => (
            <div key={`h-${h}`} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9, color: '#6E7191', fontWeight: 500,
            }}>
              {h}
            </div>
          ))}
          {/* Legend spacer */}
          <div />

          {/* Day rows */}
          {days.map(day => (
            <>
              {/* Day label */}
              <div key={`d-${day}`} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                paddingRight: 6, fontSize: 11, color: '#6E7191', fontWeight: 500,
              }}>
                {dayAbbrev[day] || day}
              </div>
              {/* Hour cells */}
              {hours.map(h => {
                const row = processedData.find(r => String(r[dayCol]) === day && String(r[hourCol]) === h)
                const val = row ? Number(row[zKey]) || 0 : 0
                return (
                  <div
                    key={`c-${day}-${h}`}
                    title={`${dayAbbrev[day] || day} ${h}:00 — ${val.toLocaleString()}`}
                    style={{
                      backgroundColor: getColor(val),
                      borderRadius: 3,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 8, fontWeight: 500,
                      color: textColor(val),
                      cursor: 'default',
                      minHeight: 20,
                      transition: 'opacity 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
                    onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                  >
                    {val > 0 ? val.toLocaleString() : ''}
                  </div>
                )
              })}
              {/* Row spacer for legend */}
              <div key={`s-${day}`} />
            </>
          ))}
        </div>

        {/* Horizontal legend bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 56, paddingTop: 6, paddingBottom: 2 }}>
          <span style={{ fontSize: 9, color: '#6E7191' }}>{minZ}</span>
          <div style={{
            flex: 1, maxWidth: 200, height: 8, borderRadius: 4,
            background: 'linear-gradient(90deg, rgba(0,102,204,0.08), rgba(0,102,204,0.5), rgba(0,61,115,0.95))',
          }} />
          <span style={{ fontSize: 9, color: '#6E7191' }}>{maxZ.toLocaleString()}</span>
        </div>
      </div>
    )
  }

  // GAUGE (rendered as a semi-circle pie)
  if (chartType === 'gauge') {
    const val = Number(processedData[0]?.[yKey]) || 0
    const maxVal = Math.max(val * 1.5, 100)
    const gaugeData = [
      { name: 'Valor', value: val },
      { name: '', value: maxVal - val },
    ]
    return (
      <div className="flex flex-col items-center justify-center" style={{ height: fillContainer ? '100%' : height }}>
        <ResponsiveContainer width="100%" height={fillContainer ? '70%' : height * 0.7}>
          <PieChart>
            <Pie
              data={gaugeData}
              dataKey="value"
              startAngle={180}
              endAngle={0}
              cx="50%"
              cy="80%"
              outerRadius="38%"
              innerRadius="28%"
            >
              <Cell fill={palette[0]} />
              <Cell fill="#E4E4E7" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="text-center -mt-4">
          <span className="text-2xl font-bold" style={{ color: palette[0] }}>{val.toLocaleString('es-CO')}</span>
          <p className="text-xs text-text-muted mt-1">{getLabel(yKey)}</p>
        </div>
      </div>
    )
  }

  // DEFAULT: bar chart (also handles 'histogram')
  // Multi-Y (bivariate): grouped bars when 3+ columns
  if (yKeys.length >= 2) {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} label={xAxisLabel} />
          <YAxis {...commonAxisProps} label={yAxisLabel} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Bar key={col} dataKey={col} fill={palette[i % palette.length]} radius={[4, 4, 0, 0]} name={getLabel(col)} />
          ))}
          <Legend wrapperStyle={legendStyle} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={processedData} onClick={handleClick}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
        <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} label={xAxisLabel} />
        <YAxis {...commonAxisProps} label={yAxisLabel} />
        <Tooltip {...tooltipStyle} />
        <Bar dataKey={yKey} fill={palette[0]} radius={[4, 4, 0, 0]} name={getLabel(yKey)}>
          {processedData.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
