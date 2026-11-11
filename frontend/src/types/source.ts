export interface DataSource {
  id: number
  code: string
  name: string
  protocol: 'opcua' | 'dcs' | 'csv'
  sample_interval_s: number
  timezone: string
  drift_hint_ms: number
  status: string
  workshop: string
  description: string
  last_capture_at?: string | null
}

export interface Signal {
  id: number
  code: string
  source_id: number
  device_code: string
  device_name: string
  measure_name: string
  tag_path: string
  unit: string
  sampling_interval_s: number
  is_active: boolean
  scale_min?: number
  scale_max?: number
}

export interface SourceDetail {
  source: DataSource
  signals: Signal[]
  raw_point_count: number
  signal_count: number
}
