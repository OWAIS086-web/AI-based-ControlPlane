import { api } from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiLineType {
  id: string
  name: string
  icon: string
  color: string
  order: number
}

export interface LineTypeCreatePayload {
  name: string
  icon: string
  color: string
}

export interface LineTypeUpdatePayload {
  name?: string
  icon?: string
  color?: string
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const lineTypesService = {
  async list(): Promise<ApiLineType[]> {
    return api.get<ApiLineType[]>('/line-types')
  },

  async create(payload: LineTypeCreatePayload): Promise<ApiLineType> {
    return api.post<ApiLineType>('/line-types', payload)
  },

  async update(id: string, payload: LineTypeUpdatePayload): Promise<ApiLineType> {
    return api.patch<ApiLineType>(`/line-types/${id}`, payload)
  },

  async remove(id: string): Promise<void> {
    return api.delete<void>(`/line-types/${id}`)
  },

  async reorder(ids: string[]): Promise<ApiLineType[]> {
    return api.patch<ApiLineType[]>('/line-types/reorder', { ids })
  },
}
