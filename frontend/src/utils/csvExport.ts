const LABELS: Record<string, string> = {
  date: 'Fecha', hora: 'Hora', count: 'Cantidad', total: 'Total',
  contact_id: 'ID Contacto', contact_name: 'Contacto', agent_id: 'Agente',
  conversations: 'Conversaciones', contacts: 'Contactos', mensajes: 'Mensajes',
  semana: 'Semana', avg_frt: 'FRT Promedio (s)', avg_handle: 'Handle Time (s)',
  total_enviados: 'Total Enviados', total_chunks: 'Total Chunks',
  campana_nombre: 'Campana', campaign_id: 'ID Campana',
  dia_semana: 'Dia Semana', value: 'Valor', bucket: 'Rango',
  reason: 'Razon', category: 'Categoria', direction: 'Direccion',
  intent: 'Intencion', sending_type: 'Tipo Envio', chunks_per_send: 'Chunks/Envio',
  fallback_rate: 'Tasa Fallback (%)', fallback_count: 'Fallback',
  msg_count: 'Mensajes', pct_over_touched: '% Sobre-tocados',
  week: 'Semana', total_contacts: 'Total Contactos', over_touched: 'Sobre-tocados',
}

function getHeader(col: string): string {
  return LABELS[col] || col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function exportCsv(
  data: Record<string, any>[],
  columns: string[],
  filename: string,
) {
  if (!data.length) return

  const BOM = '\uFEFF'
  const headers = columns.map(getHeader)
  const rows = data.map(row =>
    columns.map(col => {
      const val = row[col]
      if (val === null || val === undefined) return ''
      const s = String(val)
      return s.includes(',') || s.includes('"') || s.includes('\n')
        ? `"${s.replace(/"/g, '""')}"`
        : s
    }).join(',')
  )

  const csv = BOM + [headers.join(','), ...rows].join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const today = new Date().toISOString().slice(0, 10)
  a.href = url
  a.download = `${filename}_${today}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
