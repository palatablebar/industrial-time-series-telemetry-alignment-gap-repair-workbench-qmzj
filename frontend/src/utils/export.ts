import { TOKEN_KEY } from './request'

function filenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utfMatch) return decodeURIComponent(utfMatch[1])
  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain ? plain[1] : fallback
}

export async function downloadCsv(path: string, fallbackName: string): Promise<number> {
  const token = localStorage.getItem(TOKEN_KEY) ?? ''
  const response = await fetch(`/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `导出失败（HTTP ${response.status}）`)
  }
  const rows = Number(response.headers.get('X-CSV-Rows') ?? '0')
  const blob = await response.blob()
  const filename = filenameFromDisposition(response.headers.get('Content-Disposition'), fallbackName)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
  return rows
}
