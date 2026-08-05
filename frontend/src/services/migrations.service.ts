import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiMigration {
  id: string
  fromLineId: string
  fromStationId: string
  toLineId: string
  toStationId: string
  processIds: string[]
  processNames: string[]
  status: 'pending' | 'completed' | 'failed'
  performedBy: string
  performedByName: string
  createdAt: string
  completedAt: string | null
}

export interface MigrationListParams {
  status?: 'pending' | 'completed' | 'failed'
  fromLineId?: string
  page?: number
  limit?: number
}

export interface CreateMigrationPayload {
  fromLineId: string
  fromStationId: string
  toLineId: string
  toStationId: string
  processIds: string[]
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const migrationsService = {
  async list(params: MigrationListParams = {}): Promise<PaginatedResponse<ApiMigration>> {
    const qs = new URLSearchParams()
    if (params.status)     qs.set('status',     params.status)
    if (params.fromLineId) qs.set('fromLineId', params.fromLineId)
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiMigration>>(`/migrations?${qs}`)
  },

  async get(migrationId: string): Promise<ApiMigration> {
    return api.get<ApiMigration>(`/migrations/${migrationId}`)
  },

  async create(payload: CreateMigrationPayload): Promise<ApiMigration> {
    return api.post<ApiMigration>('/migrations', payload)
  },
}
