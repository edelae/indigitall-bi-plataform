export interface QueryResult {
  response: string
  data: Record<string, any>[]
  columns: string[]
  chart_type: string | null
  query_details: {
    sql?: string
    function?: string
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
}

export interface TableInfo {
  table_name: string
  row_count: number
  size: string
  columns: ColumnInfo[]
}

export interface ColumnInfo {
  column_name: string
  data_type: string
  nullable: boolean
  default: string | null
}

export type ChartType = 'bar' | 'line' | 'pie' | 'area' | 'histogram' | 'table'

export const CHART_COLORS = ['#1E88E5', '#76C043', '#A0A3BD', '#42A5F5', '#1565C0', '#FFC107', '#9C27B0', '#FF5722']
