import http from './http'
import type { LoginResult, User } from '../types/user'

export async function login(email: string, password: string): Promise<LoginResult> {
  const { data } = await http.post<LoginResult>('/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<{ user: User }> {
  const { data } = await http.get<{ user: User }>('/auth/me')
  return data
}
