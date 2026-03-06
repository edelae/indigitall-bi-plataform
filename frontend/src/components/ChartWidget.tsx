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
  onClickPoint?: (point: Record<string, any>) => void
}

const LABELS: Record<string, string> = {
  date: 'Fecha', fecha: 'Fecha', messages: 'Mensajes', count: 'Cantidad',
  total: 'Total', name: 'Nombre', value: 'Valor', agent_name: 'Agente',
  contact_name: 'Contacto', status: 'Estado', hour: 'Hora', day: 'Dia',
  month: 'Mes', category: 'Categoria', channel: 'Canal', type: 'Tipo',
  rate: 'Tasa', percentage: 'Porcentaje',
}

function getLabel(col: string): string {
  const lower = col.toLowerCase()
  return LABELS[lower] || col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function ChartWidget({ data, columns, chartType, height = 300, onClickPoint }: Props) {
  const xKey = columns[0]
  const yKey = columns.length > 1 ? columns[1] : columns[0]
  const yKeys = columns.slice(1)

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

  const commonAxisProps = {
    tick: { fontSize: 12, fill: '#6E7191' },
    axisLine: { stroke: '#E4E4E7' },
    tickLine: false,
  }

  const tooltipStyle = {
    contentStyle: {
      backgroundColor: '#1A1A2E',
      border: 'none',
      borderRadius: 8,
      color: 'white',
      fontSize: 13,
      fontFamily: 'Inter',
    },
    itemStyle: { color: 'white' },
    labelStyle: { color: '#A0A3BD', marginBottom: 4 },
  }

  const rotateX = data.length > 6

  // PIE
  if (chartType === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={processedData}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={height / 3}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={{ stroke: '#A0A3BD' }}
          >
            {processedData.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip {...tooltipStyle} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  // LINE
  if (chartType === 'line') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Line key={col} type="monotone" dataKey={col} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2.5} dot={{ fill: CHART_COLORS[i % CHART_COLORS.length], r: 3 }} activeDot={{ r: 5 }} name={getLabel(col)} />
          ))}
          {yKeys.length > 1 && <Legend />}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  // AREA
  if (chartType === 'area') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Area type="monotone" dataKey={yKey} stroke={CHART_COLORS[0]} fill={`${CHART_COLORS[0]}1A`} strokeWidth={2} name={getLabel(yKey)} />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // AREA STACKED
  if (chartType === 'area_stacked') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Area key={col} type="monotone" dataKey={col} stackId="1" stroke={CHART_COLORS[i % CHART_COLORS.length]} fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={0.6} name={getLabel(col)} />
          ))}
          <Legend />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // HORIZONTAL BAR
  if (chartType === 'bar_horizontal') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={processedData} layout="vertical" onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis type="number" {...commonAxisProps} />
          <YAxis dataKey={xKey} type="category" {...commonAxisProps} width={120} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey={yKey} fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} name={getLabel(yKey)} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // STACKED BAR
  if (chartType === 'bar_stacked') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          {yKeys.map((col, i) => (
            <Bar key={col} dataKey={col} stackId="stack" fill={CHART_COLORS[i % CHART_COLORS.length]} name={getLabel(col)} />
          ))}
          <Legend />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // SCATTER
  if (chartType === 'scatter') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} name={getLabel(xKey)} />
          <YAxis dataKey={yKey} {...commonAxisProps} name={getLabel(yKey)} />
          <Tooltip {...tooltipStyle} />
          <Scatter data={processedData} fill={CHART_COLORS[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // COMBO (bar + line)
  if (chartType === 'combo' && yKeys.length >= 2) {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey={yKeys[0]} fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} name={getLabel(yKeys[0])} />
          <Line type="monotone" dataKey={yKeys[1]} stroke={CHART_COLORS[1]} strokeWidth={2.5} dot={{ fill: CHART_COLORS[1], r: 3 }} name={getLabel(yKeys[1])} />
          <Legend />
        </ComposedChart>
      </ResponsiveContainer>
    )
  }

  // FUNNEL
  if (chartType === 'funnel') {
    const funnelData = processedData.map((row, i) => ({
      name: String(row[xKey]),
      value: Number(row[yKey]) || 0,
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }))
    return (
      <ResponsiveContainer width="100%" height={height}>
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
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }))
    return (
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={treemapData}
          dataKey="size"
          nameKey="name"
          stroke="#fff"
          fill={CHART_COLORS[0]}
        >
          <Tooltip {...tooltipStyle} />
        </Treemap>
      </ResponsiveContainer>
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
      <div className="flex flex-col items-center justify-center" style={{ height }}>
        <ResponsiveContainer width="100%" height={height * 0.7}>
          <PieChart>
            <Pie
              data={gaugeData}
              dataKey="value"
              startAngle={180}
              endAngle={0}
              cx="50%"
              cy="80%"
              outerRadius={height / 3}
              innerRadius={height / 4}
            >
              <Cell fill={CHART_COLORS[0]} />
              <Cell fill="#E4E4E7" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="text-center -mt-4">
          <span className="text-2xl font-bold" style={{ color: CHART_COLORS[0] }}>{val.toLocaleString('es-CO')}</span>
          <p className="text-xs text-text-muted mt-1">{getLabel(yKey)}</p>
        </div>
      </div>
    )
  }

  // DEFAULT: bar chart (also handles 'histogram')
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={processedData} onClick={handleClick}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
        <XAxis dataKey={xKey} {...commonAxisProps} angle={rotateX ? -45 : 0} textAnchor={rotateX ? 'end' : 'middle'} height={rotateX ? 60 : 30} />
        <YAxis {...commonAxisProps} />
        <Tooltip {...tooltipStyle} />
        <Bar dataKey={yKey} fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} name={getLabel(yKey)}>
          {processedData.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
