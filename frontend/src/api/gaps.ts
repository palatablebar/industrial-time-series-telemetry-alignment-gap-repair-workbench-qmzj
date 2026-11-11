import http from './http'
import type { GapEvent } from '../types/gap'

export interface GapFilters {
  run_id?: number
  severity?: string
  device_code?: string
}

export async function fetchGaps(filters: GapFilters = {}): Promise<{ items: GapEvent[]; total: number }> {
  const { data } = await http.get<{ items: GapEvent[]; total: number }>('/gap-events', { params: filters })
  return data
}

export async function annotateGap(gapId: number, annotation: string): Promise<{ gap: Record<string, unknown> }> {
  const { data } = await http.patch<{ gap: Record<string, unknown> }>(`/gap-events/${gapId}/annotate`, {
    annotation,
  })
  return data
}
