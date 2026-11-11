export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

export function formatSigned(value: number | null | undefined, digits = 1, unit = ''): string {
  if (value === null || value === undefined) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}${unit}`
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(digits)}%`
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  const total = Math.round(seconds)
  if (total < 60) return `${total}s`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    return `${hours}h${(minutes % 60).toString().padStart(2, '0')}m`
  }
  return `${minutes}m${rest.toString().padStart(2, '0')}s`
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace('T', ' ').replace(/-/g, '.').slice(0, 19)
}

export function formatClock(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace('T', ' ').slice(11, 19)
}

export function relativeHours(hours: number): { start: string; end: string } {
  const end = new Date()
  const start = new Date(end.getTime() - hours * 3600 * 1000)
  return { start: toLocalInput(start), end: toLocalInput(end) }
}

export function toLocalInput(date: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}:${pad(date.getSeconds())}`
}

export function shiftWindow(start: string, end: string, hours: number): { start: string; end: string } {
  const endDate = new Date(end)
  const startDate = new Date(endDate.getTime() - hours * 3600 * 1000)
  return { start: toLocalInput(startDate), end: toLocalInput(endDate) }
}
