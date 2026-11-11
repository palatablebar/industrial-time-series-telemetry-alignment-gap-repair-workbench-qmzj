import axios, { type AxiosInstance } from 'axios'
import type { ApiError } from '../types/api'

export const TOKEN_KEY = 'tsalign_token'

export function createHttp(baseURL = '/api'): AxiosInstance {
  const instance = axios.create({ baseURL, timeout: 60000 })

  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status: number | undefined = error.response?.status
      const data = error.response?.data ?? {}
      const normalized: ApiError = {
        code: data.code ?? 'TSA-5000',
        message: data.message ?? '网络请求失败，请稍后重试',
        detail: data.detail,
        requestId: data.request_id ?? error.response?.headers?.['x-request-id'] ?? null,
        status,
      }
      if (status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(normalized)
    },
  )
  return instance
}
