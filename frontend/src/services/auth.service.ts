import { api } from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LoginPayload {
  email: string
  password: string
}

export interface AuthResponse {
  accessToken: string
  refreshToken: string
  expiresIn: number
  user: ApiUser
}

export interface RefreshResponse {
  accessToken: string
  expiresIn: number
}

export interface ApiUser {
  id: string
  name: string
  email: string
  role: 'process_manager' | 'line_manager'
  status: 'active' | 'inactive'
  avatar: string
  createdAt: string
  updatedAt: string
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const authService = {
  async login(payload: LoginPayload): Promise<AuthResponse> {
    return api.post<AuthResponse>('/auth/login', payload, true)
  },

  async logout(): Promise<void> {
    return api.post('/auth/logout')
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return api.post('/auth/change-password', { currentPassword, newPassword })
  },

  async getVersion(): Promise<string> {
    const data = await api.get<{ version: string }>('/health')
    return data.version ?? ''
  },

}
