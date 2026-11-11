import { defineStore } from 'pinia'
import { fetchRunDetail, fetchRuns } from '../api/runs'
import type { RunDetail, RunSummary } from '../types/run'

interface RunState {
  items: RunSummary[]
  detail: RunDetail | null
  loading: boolean
  error: string
}

export const useRunStore = defineStore('run', {
  state: (): RunState => ({ items: [], detail: null, loading: false, error: '' }),
  actions: {
    async loadList() {
      this.loading = true
      try {
        this.items = (await fetchRuns()).items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '运行列表加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(runId: number) {
      this.loading = true
      this.error = ''
      try {
        this.detail = (await fetchRunDetail(runId)).run
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '运行详情加载失败'
      } finally {
        this.loading = false
      }
    },
  },
})
