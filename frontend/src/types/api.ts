export interface ApiError {
  code: string
  message: string
  detail?: Record<string, unknown>
  requestId?: string | null
  status?: number
}

export interface ListResponse<T> {
  items: T[]
  total?: number
}

export interface Quota {
  daily_quota: number
  quota_used: number
  quota_remaining: number
}
