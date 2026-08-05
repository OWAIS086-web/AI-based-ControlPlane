import { api } from '@/services/api'
import type { ApiUser } from '@/services/auth.service'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiLine {
  id: string
  name: string
  icon: string
  color: string
  stationCount: number
  managerId: string | null
  manager: ApiUser | null
  lineTypeId: string | null
  order: number
}

export interface AssignManagerPayload {
  managerId: string | null
}

export interface LineCreatePayload {
  name: string
  icon: string
  color: string
  lineTypeId: string | null
}

export interface LineUpdatePayload {
  name?: string
  icon?: string
  color?: string
  lineTypeId?: string | null
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const linesService = {
  async list(): Promise<ApiLine[]> {
    return api.get<ApiLine[]>('/lines')
  },

  async get(lineId: string): Promise<ApiLine> {
    return api.get<ApiLine>(`/lines/${lineId}`)
  },

  async create(payload: LineCreatePayload): Promise<ApiLine> {
    return api.post<ApiLine>('/lines', payload)
  },

  async update(lineId: string, payload: LineUpdatePayload): Promise<ApiLine> {
    return api.patch<ApiLine>(`/lines/${lineId}`, payload)
  },

  async remove(lineId: string): Promise<void> {
    return api.delete<void>(`/lines/${lineId}`)
  },

  async reorder(ids: string[]): Promise<ApiLine[]> {
    return api.patch<ApiLine[]>('/lines/reorder', { ids })
  },

  async assignManager(lineId: string, payload: AssignManagerPayload): Promise<ApiLine> {
    return api.patch<ApiLine>(`/lines/${lineId}/manager`, payload)
  },
}
