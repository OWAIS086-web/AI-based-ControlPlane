import { mApi } from './maintenanceApi'
import type {
  MaintenanceUser,
  FaultRecord,
  FaultComment,
  FaultListResponse,
  FaultFilter,
  CreateFaultBody,
  UpdateFaultBody,
} from '@/types/maintenance'

// ── Auth ─────────────────────────────────────────────────────────────────────

export const maintenanceAuthService = {
  login: (email: string, password: string) =>
    mApi.post<{ accessToken: string; refreshToken: string; expiresIn: number; user: MaintenanceUser }>(
      '/auth/login',
      { email, password },
    ),
  logout: () => mApi.post('/auth/logout'),
  changePassword: (currentPassword: string, newPassword: string) =>
    mApi.post('/auth/change-password', { currentPassword, newPassword }),
}

// ── Users ─────────────────────────────────────────────────────────────────────

export const maintenanceUserService = {
  me:        ()                                => mApi.get<MaintenanceUser>('/users/me'),
  list:      ()                                => mApi.get<MaintenanceUser[]>('/users'),
  create:    (body: object)                    => mApi.post<MaintenanceUser>('/users', body),
  update:    (id: string, body: object)        => mApi.patch<MaintenanceUser>(`/users/${id}`, body),
  setStatus: (id: string, status: string)      => mApi.patch<MaintenanceUser>(`/users/${id}/status`, { status }),
  delete:    (id: string)                      => mApi.delete(`/users/${id}`),
}

// ── Faults ────────────────────────────────────────────────────────────────────

export const maintenanceFaultService = {
  list: (filters?: FaultFilter) => {
    const params = new URLSearchParams()
    if (filters) {
      if (filters.page)              params.append('page', String(filters.page))
      if (filters.page_size)         params.append('page_size', String(filters.page_size))
      if (filters.status)            params.append('status', filters.status)
      if (filters.severity)          params.append('severity', filters.severity)
    }
    const qs = params.toString() ? `?${params.toString()}` : ''
    return mApi.get<FaultListResponse>(`/faults${qs}`)
  },
  getById: (id: string)                 => mApi.get<FaultRecord>(`/faults/${id}`),
  create:  (body: CreateFaultBody)      => mApi.post<FaultRecord>('/faults', body),
  update:  (id: string, body: UpdateFaultBody) => mApi.patch<FaultRecord>(`/faults/${id}`, body),
  delete:  (id: string)                 => mApi.delete(`/faults/${id}`),
}

// ── Comments ─────────────────────────────────────────────────────────────────

export const maintenanceCommentService = {
  list:   (faultId: string)              => mApi.get<FaultComment[]>(`/faults/${faultId}/comments`),
  create: (faultId: string, body: string) => mApi.post<FaultComment>(`/faults/${faultId}/comments`, { body }),
  delete: (faultId: string, commentId: string) => mApi.delete(`/faults/${faultId}/comments/${commentId}`),
}
