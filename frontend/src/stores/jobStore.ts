import { defineStore } from 'pinia'
import { createJob, fetchJobs, rerunJob, type JobCreatePayload } from '../api/jobs'
import type { AlignmentJob } from '../types/job'

interface JobState {
  items: AlignmentJob[]
  loading: boolean
  submitting: boolean
  error: string
}

export const useJobStore = defineStore('job', {
  state: (): JobState => ({ items: [], loading: false, submitting: false, error: '' }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.items = (await fetchJobs()).items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '任务列表加载失败'
      } finally {
        this.loading = false
      }
    },
    async submit(payload: JobCreatePayload): Promise<AlignmentJob> {
      this.submitting = true
      this.error = ''
      try {
        const result = await createJob(payload)
        this.items = [result.job, ...this.items]
        return result.job
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '任务创建失败'
        throw error
      } finally {
        this.submitting = false
      }
    },
    async rerun(jobId: number): Promise<AlignmentJob> {
      const result = await rerunJob(jobId)
      return result.job
    },
  },
})
