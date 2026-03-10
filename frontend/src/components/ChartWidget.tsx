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

  // HEATMAP (rendered as colored grid)
  if (chartType === 'heatmap' && columns.length >= 3) {
    const zKey = columns[2]
    // Order days Lun-Dom if present
    const dayOrder = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
    const rawY = [...new Set(processedData.map(r => String(r[yKey])))]
    const yValues = rawY.some(v => dayOrder.includes(v))
      ? dayOrder.filter(d => rawY.includes(d))
      : rawY
    // Sort X numerically if possible (hours 0-23)
    const rawX = [...new Set(processedData.map(r => String(r[xKey])))]
    const xValues = rawX.every(v => !isNaN(Number(v)))
      ? rawX.sort((a, b) => Number(a) - Number(b))
      : rawX

    const allZ = processedData.map(r => Number(r[zKey]) || 0)
    const minZ = Math.min(...allZ)
    const maxZ = Math.max(...allZ)
    const rangeZ = maxZ - minZ || 1

    const yLabelW = 80
    const legendW = 24
    const cellW = Math.max(Math.floor(((fillContainer ? 600 : height * 1.8) - yLabelW - legendW) / xValues.length), 28)
    const cellH = Math.max(Math.floor((fillContainer ? 240 : height - 40) / yValues.length), 22)
    const totalW = cellW * xValues.length + yLabelW + legendW + 8
    const totalH = cellH * yValues.length + 30

    const getColor = (val: number) => {
      const t = (val - minZ) / rangeZ
      if (t < 0.5) {
        const s = t / 0.5
        const r = Math.round(232 + (0 - 232) * s)
        const g = Math.round(244 + (102 - 244) * s)
        const b = Math.round(253 + (204 - 253) * s)
        return `rgb(${r},${g},${b})`
      }
      const s = (t - 0.5) / 0.5
      const r = Math.round(0 + (0 - 0) * s)
      const g = Math.round(102 + (61 - 102) * s)
      const b = Math.round(204 + (115 - 204) * s)
      return `rgb(${r},${g},${b})`
    }
    const textColor = (val: number) => ((val - minZ) / rangeZ) > 0.4 ? '#fff' : '#374151'

    return (
      <div style={{ width: '100%', height: fillContainer ? '100%' : height, overflow: 'auto', position: 'relative' }}>
        <svg width={Math.max(totalW, 300)} height={Math.max(totalH, 120)} style={{ fontFamily: ff }}>
          {/* X axis labels (top) */}
          {xValues.map((xv, xi) => (
            <text key={`xl-${xi}`} x={yLabelW + xi * cellW + cellW / 2} y={12} textAnchor="middle" fontSize={10} fill="#6E7191">{xv}</text>
          ))}
          {/* Rows */}
          {yValues.map((yv, yi) => (
            <g key={`row-${yi}`}>
              <text x={yLabelW - 6} y={20 + yi * cellH + cellH / 2 + 4} textAnchor="end" fontSize={10} fill="#6E7191">{yv}</text>
              {xValues.map((xv, xi) => {
                const row = processedData.find(r => String(r[xKey]) === xv && String(r[yKey]) === yv)
                const val = row ? Number(row[zKey]) || 0 : 0
                return (
                  <g key={`cell-${yi}-${xi}`}>
                    <rect x={yLabelW + xi * cellW} y={18 + yi * cellH} width={cellW - 2} height={cellH - 2} rx={4} fill={getColor(val)} />
                    <text x={yLabelW + xi * cellW + cellW / 2} y={18 + yi * cellH + cellH / 2 + 4} textAnchor="middle" fontSize={cellW > 32 ? 10 : 8} fill={textColor(val)} fontWeight="500">{val}</text>
                  </g>
                )
              })}
            </g>
          ))}
          {/* Color scale legend */}
          <defs>
            <linearGradient id="hm-grad" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#E8F4FD" />
              <stop offset="50%" stopColor="#0066CC" />
              <stop offset="100%" stopColor="#003D73" />
            </linearGradient>
          </defs>
          <rect x={yLabelW + xValues.length * cellW + 8} y={18} width={14} height={yValues.length * cellH} rx={4} fill="url(#hm-grad)" />
          <text x={yLabelW + xValues.length * cellW + 15} y={16} textAnchor="middle" fontSize={8} fill="#6E7191">{maxZ}</text>
          <text x={yLabelW + xValues.length * cellW + 15} y={22 + yValues.length * cellH} textAnchor="middle" fontSize={8} fill="#6E7191">{minZ}</text>
        </svg>
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
