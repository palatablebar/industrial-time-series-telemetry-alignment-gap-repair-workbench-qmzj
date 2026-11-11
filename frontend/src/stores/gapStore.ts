import { defineStore } from 'pinia'
import { annotateGap, fetchGaps, type GapFilters } from '../api/gaps'
import type { GapEvent } from '../types/gap'

interface GapState {
  items: GapEvent[]
  loading: boolean
  error: string
  filters: GapFilters
}

export const useGapStore = defineStore('gap', {
  state: (): GapState => ({ items: [], loading: false, error: '', filters: {} }),
  getters: {
    total: (state): number => state.items.length,
    bySeverity: (state) => ({
      high: state.items.filter((item) => item.severity === 'high').length,
      medium: state.items.filter((item) => item.severity === 'medium').length,
      low: state.items.filter((item) => item.severity === 'low').length,
    }),
  },
  actions: {
    async load(filters: GapFilters = {}) {
      this.loading = true
      this.error = ''
      this.filters = filters
      try {
        this.items = (await fetchGaps(filters)).items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '缺口事件加载失败'
      } finally {
        this.loading = false
      }
    },
    async annotate(gapId: number, text: string) {
      await annotateGap(gapId, text)
      const target = this.items.find((item) => item.id === gapId)
      if (target) {
        target.annotated = true
        target.annotation = text
      }
    },
  },
})
