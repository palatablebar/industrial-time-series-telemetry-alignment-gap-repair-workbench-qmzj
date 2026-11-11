export interface GapEvent {
  id: number
  run_id: number
  run_name: string
  signal_code: string
  device_code: string
  device_name: string
  measure_name: string
  unit: string
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
