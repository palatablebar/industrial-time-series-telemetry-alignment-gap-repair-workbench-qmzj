import { defineStore } from 'pinia'
import { fetchAuditTrail, fetchReportSummary, type ReportSummary } from '../api/reports'

interface ReportState {
  summary: ReportSummary | null
  audit: Array<Record<string, unknown>>
  loading: boolean
  error: string
}

export const useReportStore = defineStore('report', {
  state: (): ReportState => ({ summary: null, audit: [], loading: false, error: '' }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.summary = await fetchReportSummary()
        this.audit = (await fetchAuditTrail()).items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '质量报告加载失败'
      } finally {
        this.loading = false
      }
    },
  },
})
