import http from './http'
import type { RunDetail, RunSummary } from '../types/run'
import { downloadCsv } from '../utils/export'

export async function fetchRuns(): Promise<{ items: RunSummary[] }> {
  const { data } = await http.get<{ items: RunSummary[] }>('/alignment-runs')
  return data
}

export async function fetchRunDetail(runId: number): Promise<{ run: RunDetail }> {
  const { data } = await http.get<{ run: RunDetail }>(`/alignment-runs/${runId}`)
  return data
}

export async function exportRunCsv(runId: number): Promise<number> {
  return downloadCsv(`/alignment-runs/${runId}/export.csv`, `tsalign-run-${runId}.csv`)
}
