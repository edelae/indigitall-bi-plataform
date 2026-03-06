import type { QueryResult, SavedQuery, Dashboard, TableInfo, ChatMessage } from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// AI Chat
export async function sendChat(
  message: string,
  conversationHistory: ChatMessage[] = [],
  tenant?: string,
): Promise<QueryResult> {
  return request('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
      tenant,
    }),
  })
}

// Queries
export async function listQueries(params?: {
  limit?: number
  search?: string
  favorites_only?: boolean
  tenant?: string
}): Promise<{ queries: SavedQuery[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.search) searchParams.set('search', params.search)
  if (params?.favorites_only) searchParams.set('favorites_only', 'true')
  if (params?.tenant) searchParams.set('tenant', params.tenant)
  const qs = searchParams.toString()
  return request(`/queries${qs ? '?' + qs : ''}`)
}

export async function getQuery(id: number, tenant?: string): Promise<SavedQuery> {
  const qs = tenant ? `?tenant=${tenant}` : ''
  return request(`/queries/${id}${qs}`)
}

export async function saveQuery(data: {
  name: string
  query_text: string
  data: Record<string, any>[]
  columns?: string[]
  ai_function?: string | null
  generated_sql?: string | null
  chart_type?: string | null
  conversation_history?: ChatMessage[]
  tenant?: string
}): Promise<{ success: boolean; id: number }> {
  return request('/queries', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function toggleQueryFavorite(id: number): Promise<{ success: boolean }> {
  return request(`/queries/${id}/favorite`, { method: 'POST' })
}

export async function archiveQuery(id: number): Promise<{ success: boolean }> {
  return request(`/queries/${id}/archive`, { method: 'POST' })
}

// Dashboards
export async function listDashboards(params?: {
  limit?: number
  search?: string
  tenant?: string
}): Promise<{ dashboards: Dashboard[]; total: number }> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.search) searchParams.set('search', params.search)
  if (params?.tenant) searchParams.set('tenant', params.tenant)
  const qs = searchParams.toString()
  return request(`/dashboards${qs ? '?' + qs : ''}`)
}

export async function getDashboard(id: number, tenant?: string): Promise<Dashboard> {
  const qs = tenant ? `?tenant=${tenant}` : ''
  return request(`/dashboards/${id}${qs}`)
}

export async function saveDashboard(data: {
  name: string
  description?: string
  layout: any[]
  tenant?: string
}): Promise<{ success: boolean; id: number }> {
  return request('/dashboards', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDashboard(id: number, layout: any[], tenant?: string): Promise<{ success: boolean }> {
  return request(`/dashboards/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ layout, tenant }),
  })
}

export async function toggleDashboardFavorite(id: number): Promise<{ success: boolean }> {
  return request(`/dashboards/${id}/favorite`, { method: 'POST' })
}

export async function archiveDashboard(id: number): Promise<{ success: boolean }> {
  return request(`/dashboards/${id}/archive`, { method: 'POST' })
}

// Schema
export async function listTables(): Promise<TableInfo[]> {
  return request('/schema/tables')
}

export async function previewTable(name: string, limit = 50, schema = 'public'): Promise<{
  columns: string[]
  data: Record<string, any>[]
  total: number
}> {
  return request(`/schema/tables/${name}/preview?limit=${limit}&schema=${schema}`)
}
