import { defineStore } from 'pinia'
import { fetchSourceDetail, fetchSources } from '../api/sources'
import type { DataSource, SourceDetail } from '../types/source'

interface SourceState {
  items: DataSource[]
  detail: SourceDetail | null
  loading: boolean
  error: string
}

export const useSourceStore = defineStore('source', {
  state: (): SourceState => ({ items: [], detail: null, loading: false, error: '' }),
  getters: {
    devices: (state): string[] => Array.from(new Set(state.detail?.signals.map((signal) => signal.device_code) ?? [])),
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchSources()
        this.items = result.items
        if (!this.detail && result.items.length > 0) {
          await this.select(result.items[0].id)
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '数据源加载失败'
      } finally {
        this.loading = false
      }
    },
    async select(sourceId: number) {
      try {
        this.detail = await fetchSourceDetail(sourceId)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '数据源详情加载失败'
      }
    },
  },
})
