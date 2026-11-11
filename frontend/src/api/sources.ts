import http from './http'
import type { DataSource, Signal, SourceDetail } from '../types/source'

export async function fetchSources(): Promise<{ items: DataSource[] }> {
  const { data } = await http.get<{ items: DataSource[] }>('/data-sources')
  return data
}

export async function fetchSourceDetail(sourceId: number): Promise<SourceDetail> {
  const { data } = await http.get<SourceDetail>(`/data-sources/${sourceId}`)
  return data
}

export async function fetchSignals(deviceCode?: string): Promise<{ items: Signal[] }> {
  const { data } = await http.get<{ items: Signal[] }>('/signals', { params: { device_code: deviceCode } })
  return data
}
