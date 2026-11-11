export type UserRole = 'engineer' | 'analyst' | 'viewer'

export interface User {
  id: number
  email: string
  display_name: string
  role: UserRole
  unit: string
}

export interface LoginResult {
  token: string
  user: User
}
