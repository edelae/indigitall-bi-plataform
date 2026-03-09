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

// Named color palettes for per-widget customization
export const COLOR_PALETTES: Record<string, { name: string; colors: string[] }> = {
  indigitall: { name: 'InDigitall', colors: CHART_COLORS },
  warm: { name: 'Calido', colors: ['#FF6B35', '#F7C948', '#FF4757', '#FF9F43', '#EE5A24', '#D35400', '#F39C12', '#E74C3C', '#FDCB6E', '#F8B739'] },
  cool: { name: 'Frio', colors: ['#4A90D9', '#5352ED', '#70A1FF', '#1E90FF', '#6C5CE7', '#A29BFE', '#48DBFB', '#0ABDE3', '#74B9FF', '#55E6C1'] },
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
