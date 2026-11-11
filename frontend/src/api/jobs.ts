import http from './http'
import type { AggStrategy, AlignmentJob, FillStrategy, JobEstimate } from '../types/job'

export interface JobCreatePayload {
  name?: string
  device_codes: string[]
  window_start: string
  window_end: string
  grid_s: number
  agg_strategy: AggStrategy
  fill_strategy: FillStrategy
  note?: string
}

export async function createJob(payload: JobCreatePayload): Promise<{ job: AlignmentJob; quota: Record<string, number> }> {
  const { data } = await http.post('/alignment-jobs', payload)
  return data
}

export async function fetchJobs(): Promise<{ items: AlignmentJob[] }> {
  const { data } = await http.get<{ items: AlignmentJob[] }>('/alignment-jobs')
  return data
}

export async function fetchJob(jobId: number): Promise<{ job: AlignmentJob; run_id: number | null }> {
  const { data } = await http.get<{ job: AlignmentJob; run_id: number | null }>(`/alignment-jobs/${jobId}`)
  return data
}

export async function rerunJob(jobId: number): Promise<{ job: AlignmentJob }> {
  const { data } = await http.post<{ job: AlignmentJob }>(`/alignment-jobs/${jobId}/run`)
  return data
}

export async function estimateJob(payload: {
  device_codes: string[]
  window_start: string
  window_end: string
  grid_s: number
}): Promise<JobEstimate> {
  const { data } = await http.post<JobEstimate>('/alignment-jobs/estimate', payload)
  return data
}
