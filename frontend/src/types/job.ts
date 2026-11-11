export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'
export type AggStrategy = 'mean' | 'last' | 'linear'
export type FillStrategy = 'locf' | 'linear' | 'seasonal_naive'

export interface AlignmentJob {
  id: number
  name: string
  device_codes: string[]
  signal_codes: string[]
  window_start: string
  window_end: string
  grid_s: number
  agg_strategy: AggStrategy
  fill_strategy: FillStrategy
  status: JobStatus
  error_reason: string
  note: string
  created_by_name?: string | null
  run_id?: number | null
  quality_score?: number | null
  created_at: string
}

export interface JobEstimate {
  bucket_count: number
  point_count: number
  signal_count: number
  span_seconds: number
  grid_s: number
}
