export interface QueryResult {
  response: string
  data: Record<string, any>[]
  columns: string[]
  chart_type: string | null
  query_details: {
    sql?: string
    function?: string
    title?: string
    rows_returned?: number
  } | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  result?: QueryResult
  timestamp?: string
}

export interface SavedQuery {
  id: number
  name: string
  query_text: string
  ai_function: string | null
  result_row_count: number
  result_data: Record<string, any>[]
  result_columns: { name: string; type: string }[]
  visualizations: {
    type: string
    is_default?: boolean
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
  }[]
  generated_sql: string | null
  tags: string[] | null
  is_favorite: boolean
  created_at: string
  updated_at: string
  conversation_history: ChatMessage[] | null
  folder_id?: string | null
}

export interface Dashboard {
  id: number
  name: string
  description: string | null
  layout: DashboardWidget[]
  tags: string[] | null
  is_favorite: boolean
  is_default: boolean
  created_at: string
  updated_at: string
  widget_count?: number
}

export interface DashboardWidget {
  query_id?: number
  title: string
  type: string
  chart_type?: string
  width: number
  data: Record<string, any>[]
  columns: string[]
  sql?: string
  query_text?: string
  grid_i: string
  grid_x: number
  grid_y: number
  grid_w: number
  grid_h: number
  // KPI widget
  kpi_value?: string | number
  kpi_label?: string
  kpi_delta?: number
  kpi_style?: 'minimal' | 'accent' | 'progress'
  kpi_max_value?: number
  // Text/title block
  text_content?: string
  text_url?: string
  is_title_block?: boolean
  // Editable title
  custom_title?: string
  // Per-widget color palette
  color_palette?: string
  // Per-widget axis labels
  custom_x_label?: string
  custom_y_label?: string
  show_legend?: boolean
  // Text sizing
  text_size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl'
  // Tab assignment
  tab_id?: string
  tab_name?: string
  // Font customization (Prompt 4)
  font_family?: string
  title_font_size?: number
  axis_font_size?: number
  kpi_value_font_size?: number
  legend_font_size?: number
  // Sub-tab assignment (Prompt 5)
  sub_tab_id?: string
  sub_tab_name?: string
  // Column assignment (carried from query personalization)
  x_column?: string
  y_columns?: string[]
  group_by_column?: string
  // KPI color
  kpi_color?: string
  // Card visual style
  card_style?: string
  card_bg_color?: string
  card_text_color?: string
  hide_header?: boolean
  text_align?: 'left' | 'center' | 'right'
  // Original SQL (before granularity filter transforms)
  original_sql?: string
}

// Font family options
export const FONT_FAMILIES = [
  { value: 'Inter', label: 'Inter' },
  { value: 'Roboto', label: 'Roboto' },
  { value: 'Merriweather', label: 'Merriweather' },
  { value: 'Montserrat', label: 'Montserrat' },
  { value: 'JetBrains Mono', label: 'Monospace' },
]

// Widget size presets (Prompt 2)
export const SIZE_PRESETS = [
  { label: 'XS', w: 2, h: 2 },
  { label: 'S', w: 3, h: 2 },
  { label: 'M', w: 4, h: 3 },
  { label: 'L', w: 6, h: 4 },
  { label: 'XL', w: 8, h: 4 },
  { label: 'Full', w: 12, h: 4 },
]

export interface TableInfo {
  table_name: string
  row_count: number
  size: string
  columns: ColumnInfo[]
  schema?: string
}

export interface ColumnInfo {
  column_name: string
  data_type: string
  nullable: boolean
  default: string | null
}

export interface QueryFolder {
  id: string
  name: string
  query_count?: number
}

export type ChartType =
  | 'bar' | 'bar_horizontal' | 'bar_stacked'
  | 'line' | 'pie' | 'area' | 'area_stacked'
  | 'scatter' | 'combo' | 'heatmap'
  | 'funnel' | 'treemap' | 'gauge'
  | 'histogram' | 'table' | 'kpi'

// Monochromatic blue palette — inDigitall brand
export const CHART_COLORS = [
  '#0066CC', // azul primario
  '#338FD9', // azul medio
  '#0052A3', // azul oscuro
  '#5AADE0', // azul claro
  '#003D73', // azul profundo
  '#80C4E8', // azul suave
  '#1A7AD4', // azul intermedio
  '#004D8C', // azul marino
  '#A6D6EF', // azul pastel
  '#002B54', // azul noche
]

export const PRIMARY_COLOR = '#0066CC'
export const SECONDARY_COLOR = '#0052A3'

// Named color palettes for per-widget customization
export const COLOR_PALETTES: Record<string, { name: string; colors: string[] }> = {
  indigitall: { name: 'InDigitall', colors: CHART_COLORS },
  warm: { name: 'Calido', colors: ['#FF6B35', '#F7C948', '#FF4757', '#FF9F43', '#EE5A24', '#D35400', '#F39C12', '#E74C3C', '#FDCB6E', '#F8B739'] },
  cool: { name: 'Azul Monocromático', colors: ['#0066CC', '#338FD9', '#0052A3', '#5AADE0', '#003D73', '#80C4E8', '#1A7AD4', '#004D8C', '#A6D6EF', '#002B54'] },
  nature: { name: 'Natural', colors: ['#2ECC71', '#27AE60', '#1ABC9C', '#16A085', '#3D9970', '#2ECC40', '#01A66F', '#00B894', '#55E6C1', '#7BED9F'] },
  corporate: { name: 'Corporativo', colors: ['#2C3E50', '#34495E', '#7F8C8D', '#95A5A6', '#BDC3C7', '#1E88E5', '#546E7A', '#455A64', '#78909C', '#90A4AE'] },
  vibrant: { name: 'Vibrante', colors: ['#E91E63', '#9C27B0', '#3F51B5', '#00BCD4', '#4CAF50', '#FF9800', '#F44336', '#673AB7', '#009688', '#FFC107'] },
}

export interface GridTemplate {
  id: string
  name: string
  description: string
  zones: { x: number; y: number; w: number; h: number }[]
}

export const GRID_TEMPLATES: GridTemplate[] = [
  {
    id: 'two-cols',
    name: '2 Columnas',
    description: 'Dos columnas iguales',
    zones: [
      { x: 0, y: 0, w: 6, h: 4 },
      { x: 6, y: 0, w: 6, h: 4 },
    ],
  },
  {
    id: 'three-cols',
    name: '3 Columnas',
    description: 'Tres columnas iguales',
    zones: [
      { x: 0, y: 0, w: 4, h: 4 },
      { x: 4, y: 0, w: 4, h: 4 },
      { x: 8, y: 0, w: 4, h: 4 },
    ],
  },
  {
    id: 'hero-top',
    name: 'Hero Arriba',
    description: 'Grande arriba, dos abajo',
    zones: [
      { x: 0, y: 0, w: 12, h: 4 },
      { x: 0, y: 4, w: 6, h: 4 },
      { x: 6, y: 4, w: 6, h: 4 },
    ],
  },
  {
    id: 'sidebar-left',
    name: 'Panel Izquierdo',
    description: 'Columna ancha + estrecha',
    zones: [
      { x: 0, y: 0, w: 8, h: 4 },
      { x: 8, y: 0, w: 4, h: 4 },
      { x: 8, y: 4, w: 4, h: 4 },
    ],
  },
  {
    id: 'kpi-row',
    name: 'KPIs + Graficas',
    description: '4 KPIs arriba, 2 graficas abajo',
    zones: [
      { x: 0, y: 0, w: 3, h: 2 },
      { x: 3, y: 0, w: 3, h: 2 },
      { x: 6, y: 0, w: 3, h: 2 },
      { x: 9, y: 0, w: 3, h: 2 },
      { x: 0, y: 2, w: 6, h: 4 },
      { x: 6, y: 2, w: 6, h: 4 },
    ],
  },
  {
    id: 'dashboard-full',
    name: 'Dashboard Completo',
    description: 'KPIs, tendencia, detalles',
    zones: [
      { x: 0, y: 0, w: 3, h: 2 },
      { x: 3, y: 0, w: 3, h: 2 },
      { x: 6, y: 0, w: 3, h: 2 },
      { x: 9, y: 0, w: 3, h: 2 },
      { x: 0, y: 2, w: 12, h: 4 },
      { x: 0, y: 6, w: 6, h: 4 },
      { x: 6, y: 6, w: 6, h: 4 },
    ],
  },
  {
    id: 'quad',
    name: '4 Cuadrantes',
    description: 'Cuatro graficas iguales',
    zones: [
      { x: 0, y: 0, w: 6, h: 4 },
      { x: 6, y: 0, w: 6, h: 4 },
      { x: 0, y: 4, w: 6, h: 4 },
      { x: 6, y: 4, w: 6, h: 4 },
    ],
  },
  {
    id: 'four-cols',
    name: '4 Columnas',
    description: 'Cuatro columnas iguales',
    zones: [
      { x: 0, y: 0, w: 3, h: 4 },
      { x: 3, y: 0, w: 3, h: 4 },
      { x: 6, y: 0, w: 3, h: 4 },
      { x: 9, y: 0, w: 3, h: 4 },
    ],
  },
  {
    id: 'big-left-small-right',
    name: 'Grande + 2 Pequenas',
    description: 'Una grande y dos apiladas a la derecha',
    zones: [
      { x: 0, y: 0, w: 8, h: 6 },
      { x: 8, y: 0, w: 4, h: 3 },
      { x: 8, y: 3, w: 4, h: 3 },
    ],
  },
  {
    id: 'six-grid',
    name: '6 Celdas',
    description: 'Tres columnas, dos filas',
    zones: [
      { x: 0, y: 0, w: 4, h: 3 },
      { x: 4, y: 0, w: 4, h: 3 },
      { x: 8, y: 0, w: 4, h: 3 },
      { x: 0, y: 3, w: 4, h: 3 },
      { x: 4, y: 3, w: 4, h: 3 },
      { x: 8, y: 3, w: 4, h: 3 },
    ],
  },
  {
    id: 'kpi-6-chart-3',
    name: '6 KPIs + 3 Graficas',
    description: 'KPIs arriba, tres graficas abajo',
    zones: [
      { x: 0, y: 0, w: 2, h: 2 },
      { x: 2, y: 0, w: 2, h: 2 },
      { x: 4, y: 0, w: 2, h: 2 },
      { x: 6, y: 0, w: 2, h: 2 },
      { x: 8, y: 0, w: 2, h: 2 },
      { x: 10, y: 0, w: 2, h: 2 },
      { x: 0, y: 2, w: 4, h: 4 },
      { x: 4, y: 2, w: 4, h: 4 },
      { x: 8, y: 2, w: 4, h: 4 },
    ],
  },
  {
    id: 'wide-narrow',
    name: 'Ancho + Angosto',
    description: 'Columna ancha izquierda, angosta derecha',
    zones: [
      { x: 0, y: 0, w: 9, h: 4 },
      { x: 9, y: 0, w: 3, h: 2 },
      { x: 9, y: 2, w: 3, h: 2 },
    ],
  },
  {
    id: 'mosaic',
    name: 'Mosaico',
    description: 'Tamanos variados tipo mosaico',
    zones: [
      { x: 0, y: 0, w: 4, h: 4 },
      { x: 4, y: 0, w: 8, h: 2 },
      { x: 4, y: 2, w: 4, h: 2 },
      { x: 8, y: 2, w: 4, h: 4 },
      { x: 0, y: 4, w: 8, h: 3 },
    ],
  },
]

// Dashboard-level variable filter
export interface DashboardFilter {
  id: string
  column: string            // column name to filter on (e.g. "agent_id")
  table?: string            // optional table hint
  label: string             // display label (e.g. "Agente")
  values: string[]          // available values (auto-detected from data)
  selected: string[]        // currently selected values
}

/**
 * Detect filterable columns from widgets' data.
 * Returns columns that appear in multiple widgets or have low cardinality (< 50 unique values).
 */
export function detectFilterableColumns(widgets: DashboardWidget[]): { column: string; values: string[]; table?: string }[] {
  const colMap = new Map<string, Set<string>>()
  for (const w of widgets) {
    if (!w.data?.length || !w.columns?.length) continue
    for (const col of w.columns) {
      const uniqueVals = new Set(w.data.map(r => String(r[col] ?? '')).filter(v => v !== ''))
      if (uniqueVals.size > 0 && uniqueVals.size <= 50) {
        if (!colMap.has(col)) colMap.set(col, new Set())
        for (const v of uniqueVals) colMap.get(col)!.add(v)
      }
    }
  }
  return Array.from(colMap.entries())
    .filter(([, vals]) => vals.size >= 2 && vals.size <= 50)
    .map(([col, vals]) => ({ column: col, values: Array.from(vals).sort() }))
}

/**
 * Apply dashboard filters to a SQL query by appending WHERE/AND clauses.
 */
export function applyDashboardFilters(sql: string, filters: DashboardFilter[]): string {
  if (!sql || !filters.length) return sql
  const activeFilters = filters.filter(f => f.selected.length > 0 && f.selected.length < f.values.length)
  if (!activeFilters.length) return sql

  const conditions = activeFilters.map(f => {
    const escaped = f.selected.map(v => `'${v.replace(/'/g, "''")}'`).join(', ')
    return `${f.column} IN (${escaped})`
  })

  // Inject before GROUP BY, ORDER BY, LIMIT, or at end
  const injectionPoint = sql.search(/\b(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING)\b/i)
  if (injectionPoint > 0) {
    const before = sql.slice(0, injectionPoint).trimEnd()
    const after = sql.slice(injectionPoint)
    const hasWhere = /\bWHERE\b/i.test(before)
    return `${before} ${hasWhere ? 'AND' : 'WHERE'} ${conditions.join(' AND ')} ${after}`
  }

  const hasWhere = /\bWHERE\b/i.test(sql)
  return `${sql} ${hasWhere ? 'AND' : 'WHERE'} ${conditions.join(' AND ')}`
}

// Card visual style presets
export interface CardStylePreset {
  id: string
  label: string
  bg: string
  border: string
  shadow: string
  text: string
  accent?: string
}

export const CARD_STYLE_PRESETS: CardStylePreset[] = [
  { id: 'default', label: 'Blanco', bg: '#FFFFFF', border: '1px solid #E8EAF0', shadow: '0 1px 3px rgba(0,0,0,0.04)', text: '#111827' },
  { id: 'elevated', label: 'Elevado', bg: '#FFFFFF', border: 'none', shadow: '0 8px 24px rgba(0,0,0,0.10)', text: '#111827' },
  { id: 'flat', label: 'Plano', bg: '#F3F4F6', border: 'none', shadow: 'none', text: '#374151' },
  { id: 'outlined-blue', label: 'Borde azul', bg: '#FFFFFF', border: '2px solid #1E88E5', shadow: 'none', text: '#111827' },
  { id: 'outlined-green', label: 'Borde verde', bg: '#FFFFFF', border: '2px solid #76C043', shadow: 'none', text: '#111827' },
  { id: 'dark', label: 'Oscuro', bg: '#1A1A2E', border: 'none', shadow: '0 4px 16px rgba(0,0,0,0.2)', text: '#F9FAFB' },
  { id: 'gradient-blue', label: 'Azul grad.', bg: 'linear-gradient(135deg, #1E88E5, #1565C0)', border: 'none', shadow: '0 4px 12px rgba(30,136,229,0.3)', text: '#FFFFFF' },
  { id: 'gradient-green', label: 'Verde grad.', bg: 'linear-gradient(135deg, #76C043, #2E7D32)', border: 'none', shadow: '0 4px 12px rgba(118,192,67,0.3)', text: '#FFFFFF' },
  { id: 'gradient-dark', label: 'Oscuro grad.', bg: 'linear-gradient(135deg, #1A1A2E, #2D2D44)', border: 'none', shadow: '0 4px 16px rgba(0,0,0,0.3)', text: '#FFFFFF' },
  { id: 'gradient-purple', label: 'Morado grad.', bg: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none', shadow: '0 4px 12px rgba(102,126,234,0.3)', text: '#FFFFFF' },
  { id: 'accent-left', label: 'Acento izq.', bg: '#FFFFFF', border: 'none', shadow: '0 1px 3px rgba(0,0,0,0.04)', text: '#111827', accent: '4px solid #1E88E5' },
  { id: 'accent-green', label: 'Acento verde', bg: '#FFFFFF', border: 'none', shadow: '0 1px 3px rgba(0,0,0,0.04)', text: '#111827', accent: '4px solid #76C043' },
]

// Dashboard-level granularity options
export type DashboardGranularity = 'original' | 'dia_semana' | 'mes' | 'anio'

export const GRANULARITY_OPTIONS: { value: DashboardGranularity; label: string }[] = [
  { value: 'original', label: 'Original' },
  { value: 'dia_semana', label: 'Dia semana' },
  { value: 'mes', label: 'Mes' },
  { value: 'anio', label: 'Año' },
]

export function transformSqlGranularity(sql: string, granularity: DashboardGranularity): string {
  if (granularity === 'original' || !sql) return sql
  const pattern = /DATE_TRUNC\s*\(\s*'(?:month|week|day)'\s*,\s*([\s\S]*?)\)(?:::date)?/gi
  switch (granularity) {
    case 'dia_semana':
      return sql.replace(pattern, "TRIM(TO_CHAR($1, 'Day'))")
    case 'mes':
      return sql.replace(pattern, "TRIM(TO_CHAR($1, 'Month'))")
    case 'anio':
      return sql.replace(pattern, "EXTRACT(YEAR FROM $1)::text")
    default:
      return sql
  }
}

export function getCardStyle(preset?: string): React.CSSProperties {
  const p = CARD_STYLE_PRESETS.find(s => s.id === preset) || CARD_STYLE_PRESETS[0]
  const isGradient = p.bg.includes('gradient')
  return {
    background: isGradient ? p.bg : p.bg,
    backgroundColor: isGradient ? undefined : p.bg,
    border: p.border,
    boxShadow: p.shadow,
    color: p.text,
    borderRadius: 12,
    ...(p.accent ? { borderLeft: p.accent } : {}),
  }
}
