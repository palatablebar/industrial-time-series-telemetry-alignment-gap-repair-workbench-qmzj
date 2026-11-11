export interface DriftEvidence {
  reference_signal: string
  peer_signal: string
  peer_source: string
  lag_ms: number
  correlation: number
}

export interface DriftItem {
  source_id: number
  source_code: string
  drift_ms: number
  confidence: number
  is_anchor?: boolean
  is_estimated?: boolean
  correction_ms?: number
  evidence?: DriftEvidence[]
}

export interface ClockCorrection {
  source_id: number
  source_code: string
  drift_ms: number
  correction_ms: number
  confidence: number
  is_anchor: boolean
}

export interface OverlapSourceStat {
  source_code: string
  buckets: number
  selected_buckets: number
}

export interface OverlapEvent {
  bucket: number
  start_ts: number
  end_ts: number
  sources: string[]
  selected_source: string
  selected_signal: string
}

export interface OverlapLedger {
  signal_code: string
  device_code: string
  measure_name: string
  overlap_buckets: number
  source_buckets: OverlapSourceStat[]
  events: OverlapEvent[]
}

export interface SeriesItem {
  signal_index: number
  signal_code: string
  device_code: string
  device_name: string
  measure_name: string
  unit: string
  source_code: string
  source_codes?: string[]
  member_signal_codes?: string[]
  bucket_count: number
  start_ts: number
  observed_count: number
  coverage: number
  values: (number | null)[]
  observed: boolean[]
  gap_filled?: boolean[]
  provenance?: string[]
  contributors?: string[][]
}

export interface RunGap {
  id: number
  signal_code: string
  device_code: string
  measure_name: string
  source_code?: string
  source_codes?: string[]
  start_ts: string
  end_ts: string
  duration_s: number
  bucket_length: number
  fill_strategy: string
  confidence: number
  severity: 'low' | 'medium' | 'high'
  annotated: boolean
  annotation: string
}

export interface RunSummary {
  id: number
  job_id: number
  job_name: string
  status: 'running' | 'completed' | 'failed'
  started_at: string | null
  finished_at: string | null
  duration_ms: number
  coverage_pct: number
  drift_ms: number
  drift_confidence: number
  anomaly_rate: number
  quality_score: number
  gap_count: number
  gap_total_s: number
  point_count: number
  bucket_count: number
  failure_reason: string
  created_by_name?: string | null
}

export interface QualityComponents {
  coverage?: number
  anomaly_rate?: number
  drift_score?: number
  max_abs_drift_ms?: number
  quality_score?: number
  gap_count?: number
  gap_total_s?: number
  formula?: string
}

export interface RunDetail extends RunSummary {
  t0: string
  grid_s: number
  window_start: string
  window_end: string
  agg_strategy: string
  fill_strategy: string
  drift: DriftItem[]
  corrections: ClockCorrection[]
  overlaps: OverlapLedger[]
  series: SeriesItem[]
  gaps: RunGap[]
  components: QualityComponents
  signal_coverage: Array<Record<string, unknown>>
}
