import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'
import type { ApiUser } from '@/services/auth.service'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface CreateUserPayload {
  name: string
  email: string
  role: 'process_manager' | 'line_manager'
  password: string
}

export interface UpdateUserPayload {
  name?: string
  email?: string
}

export interface UserStatusPayload {
  status: 'active' | 'inactive'
}

export interface UserSettings {
  userId: string
  notifications: {
    newUploads: boolean
    migrations: boolean
    userChanges: boolean
    systemAlerts: boolean
  }
  dataRetentionDays: number
  updatedAt: string
}

export interface UpdateSettingsPayload {
  notifications?: Partial<UserSettings['notifications']>
  dataRetentionDays?: number
}

export interface UsersListParams {
  role?: 'process_manager' | 'line_manager'
  status?: 'active' | 'inactive'
  page?: number
  limit?: number
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const usersService = {
  async list(params: UsersListParams = {}): Promise<PaginatedResponse<ApiUser>> {
    const qs = new URLSearchParams()
    if (params.role)   qs.set('role',   params.role)
    if (params.status) qs.set('status', params.status)
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiUser>>(`/users?${qs}`)
  },

  async create(payload: CreateUserPayload): Promise<ApiUser> {
    return api.post<ApiUser>('/users', payload)
  },

  async update(userId: string, payload: UpdateUserPayload): Promise<ApiUser> {
    return api.patch<ApiUser>(`/users/${userId}`, payload)
  },

  async setStatus(userId: string, payload: UserStatusPayload): Promise<ApiUser> {
    return api.patch<ApiUser>(`/users/${userId}/status`, payload)
  },

  async remove(userId: string): Promise<void> {
    return api.delete(`/users/${userId}`)
  },

  async getSettings(userId: string): Promise<UserSettings> {
    return api.get<UserSettings>(`/users/${userId}/settings`)
  },

  async updateSettings(userId: string, payload: UpdateSettingsPayload): Promise<UserSettings> {
    return api.patch<UserSettings>(`/users/${userId}/settings`, payload)
  },
}
