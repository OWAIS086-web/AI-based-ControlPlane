import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiStation {
  id: string
  name: string
  lineId: string
  processCount: number
  createdAt: string
  updatedAt: string
}

export interface CreateStationPayload {
  name: string
}

export interface StationListParams {
  page?: number
  limit?: number
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const stationsService = {
  async list(lineId: string, params: StationListParams = {}): Promise<PaginatedResponse<ApiStation>> {
    const qs = new URLSearchParams()
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiStation>>(`/lines/${lineId}/stations?${qs}`)
  },

  async create(lineId: string, payload: CreateStationPayload): Promise<ApiStation> {
    return api.post<ApiStation>(`/lines/${lineId}/stations`, payload)
  },

  async update(lineId: string, stationId: string, payload: { name: string }): Promise<ApiStation> {
    return api.patch<ApiStation>(`/lines/${lineId}/stations/${stationId}`, payload)
  },

  async remove(lineId: string, stationId: string): Promise<void> {
    return api.delete(`/lines/${lineId}/stations/${stationId}`)
  },
}
