import http from './http'

export interface ReportSummary {
  customer: string
  generated_at: string
  run_count: number
  completed_runs: number
  average_quality: number
  best_coverage: number
  total_gaps: number
  formula: string
  quality_trend: Array<Record<string, unknown>>
  drift_table: Array<Record<string, unknown>>
  gap_severity: Array<{ severity: string; count: number }>
  recent_runs: Array<Record<string, unknown>>
  quota: Record<string, number>
}

export async function fetchReportSummary(): Promise<ReportSummary> {
  const { data } = await http.get<ReportSummary>('/reports/summary')
  return data
}

export async function fetchAuditTrail(): Promise<{ items: Array<Record<string, unknown>> }> {
  const { data } = await http.get<{ items: Array<Record<string, unknown>> }>('/reports/audit')
  return data
}
