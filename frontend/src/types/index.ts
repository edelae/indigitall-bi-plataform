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
  visualizations: { type: string; is_default?: boolean }[]
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
  // Text/title block
  text_content?: string
  text_url?: string
  is_title_block?: boolean
  // Editable title
  custom_title?: string
}

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

// InDigitall institutional palette — PROMPT 3
export const CHART_COLORS = [
  '#0066CC', // azul primario
  '#00A86B', // verde secundario
  '#0099FF', // azul claro
  '#005299', // azul oscuro
  '#33BB88', // verde claro
  '#003D73', // azul muy oscuro
  '#66CCFF', // azul muy claro
  '#007A50', // verde oscuro
  '#99DDFF', // azul pastel
  '#00CC88', // verde brillante
]

export const PRIMARY_COLOR = '#0066CC'
export const SECONDARY_COLOR = '#00A86B'

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
]
