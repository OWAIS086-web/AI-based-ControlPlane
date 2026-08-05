import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiCarModel {
  id: string
  name: string
  code: string
  color: string
  status: 'active' | 'archived'
  createdAt: string
  updatedAt: string
}

export interface CarModelListParams {
  status?: 'active' | 'archived'
  page?: number
  limit?: number
}

export interface CreateCarModelPayload {
  name: string
  code: string
  color: string
}

export interface UpdateCarModelPayload {
  name?: string
  code?: string
  color?: string
}

export interface CarModelStatusPayload {
  status: 'active' | 'archived'
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const carModelsService = {
  async list(params: CarModelListParams = {}): Promise<PaginatedResponse<ApiCarModel>> {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiCarModel>>(`/car-models?${qs}`)
  },

  async create(payload: CreateCarModelPayload): Promise<ApiCarModel> {
    return api.post<ApiCarModel>('/car-models', payload)
  },

  async update(modelId: string, payload: UpdateCarModelPayload): Promise<ApiCarModel> {
    return api.patch<ApiCarModel>(`/car-models/${modelId}`, payload)
  },

  async setStatus(modelId: string, payload: CarModelStatusPayload): Promise<ApiCarModel> {
    return api.patch<ApiCarModel>(`/car-models/${modelId}/status`, payload)
  },
}
