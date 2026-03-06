import { useMemo } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
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

// Label translation
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

  // Make sure numeric values are actually numbers
  const processedData = useMemo(() => {
    return data.map(row => {
      const newRow = { ...row }
      if (typeof newRow[yKey] === 'string') {
        const num = parseFloat(newRow[yKey].replace(/,/g, '').replace(/%/g, ''))
        if (!isNaN(num)) newRow[yKey] = num
      }
      return newRow
    })
  }, [data, yKey])

  const handleClick = (point: any) => {
    if (onClickPoint && point?.activePayload?.[0]) {
      onClickPoint(point.activePayload[0].payload)
    }
  }

  if (chartType === 'table' || !data.length || columns.length < 2) {
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

  if (chartType === 'line') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} angle={data.length > 6 ? -45 : 0} textAnchor={data.length > 6 ? 'end' : 'middle'} height={data.length > 6 ? 60 : 30} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Line type="monotone" dataKey={yKey} stroke="#1E88E5" strokeWidth={2.5} dot={{ fill: '#1E88E5', r: 3 }} activeDot={{ r: 5 }} name={getLabel(yKey)} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  if (chartType === 'area') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={processedData} onClick={handleClick}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
          <XAxis dataKey={xKey} {...commonAxisProps} />
          <YAxis {...commonAxisProps} />
          <Tooltip {...tooltipStyle} />
          <Area type="monotone" dataKey={yKey} stroke="#1E88E5" fill="rgba(30,136,229,0.1)" strokeWidth={2} name={getLabel(yKey)} />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  // Default: bar chart (also handles 'histogram')
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={processedData} onClick={handleClick}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E7" />
        <XAxis dataKey={xKey} {...commonAxisProps} angle={data.length > 6 ? -45 : 0} textAnchor={data.length > 6 ? 'end' : 'middle'} height={data.length > 6 ? 60 : 30} />
        <YAxis {...commonAxisProps} />
        <Tooltip {...tooltipStyle} />
        <Bar dataKey={yKey} fill="#1E88E5" radius={[4, 4, 0, 0]} name={getLabel(yKey)}>
          {processedData.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
