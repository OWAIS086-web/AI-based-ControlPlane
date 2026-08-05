import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'
import type { ApiCarModel } from '@/services/carModels.service'
import type { ApiProcessVersion } from '@/services/versions.service'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiProcess {
  id: string
  name: string
  code: string
  extractedCode?: string | null
  lineId: string
  stationId: string
  carModelId: string
  carModel?: ApiCarModel
  status: 'active' | 'archived'
  hasMissingCp: boolean
  aiStatus: 'idle' | 'ai_running' | 'completed' | 'failed'
  versionCount: number
  latestVersion?: ApiProcessVersion
  workerId?: string | null
  workerName?: string | null
  createdAt: string
  updatedAt: string
}

export interface ProcessListParams {
  lineId?: string
  stationId?: string
  carModelId?: string
  status?: 'active' | 'archived'
  hasMissingCP?: boolean
  search?: string
  page?: number
  limit?: number
}

export interface CreateProcessPayload {
  name: string
  carModelId: string
}

export interface ProcessStatusPayload {
  status: 'active' | 'archived'
}

export interface ImportProcessesPayload {
  processIds: string[]
  carModelId: string
  mode: 'copy' | 'reference'
}

const PAGE_LIMIT = 100 // backend hard cap

function buildQs(params: ProcessListParams, page: number): URLSearchParams {
  const qs = new URLSearchParams()
  if (params.lineId)      qs.set('lineId',      params.lineId)
  if (params.stationId)   qs.set('stationId',   params.stationId)
  if (params.carModelId)  qs.set('carModelId',  params.carModelId)
  if (params.status)      qs.set('status',      params.status)
  if (params.search)      qs.set('search',      params.search)
  if (params.hasMissingCP !== undefined) qs.set('hasMissingCP', String(params.hasMissingCP))
  qs.set('page',  String(page))
  qs.set('limit', String(Math.min(params.limit ?? PAGE_LIMIT, PAGE_LIMIT)))
  return qs
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const processesService = {
  async list(params: ProcessListParams = {}): Promise<PaginatedResponse<ApiProcess>> {
    return api.get<PaginatedResponse<ApiProcess>>(`/processes?${buildQs(params, params.page ?? 1)}`)
  },

  /** Fetches every page and returns all items in one array. */
  async listAll(params: Omit<ProcessListParams, 'page' | 'limit'> = {}): Promise<ApiProcess[]> {
    const first = await api.get<PaginatedResponse<ApiProcess>>(
      `/processes?${buildQs(params, 1)}`,
    )
    const results = [...first.data]
    const remaining = first.meta.totalPages - 1
    if (remaining > 0) {
      const pages = await Promise.all(
        Array.from({ length: remaining }, (_, i) =>
          api.get<PaginatedResponse<ApiProcess>>(`/processes?${buildQs(params, i + 2)}`),
        ),
      )
      pages.forEach(p => results.push(...p.data))
    }
    return results
  },

  async get(processId: string): Promise<ApiProcess> {
    return api.get<ApiProcess>(`/processes/${processId}`)
  },

  async create(
    lineId: string,
    stationId: string,
    payload: CreateProcessPayload,
  ): Promise<ApiProcess> {
    return api.post<ApiProcess>(`/lines/${lineId}/stations/${stationId}/processes`, payload)
  },

  async setStatus(processId: string, payload: ProcessStatusPayload): Promise<ApiProcess> {
    return api.patch<ApiProcess>(`/processes/${processId}/status`, payload)
  },

  async delete(processId: string): Promise<void> {
    return api.delete(`/processes/${processId}`)
  },

  async bulkSetStatus(ids: string[], status: 'active' | 'archived'): Promise<{ updated: number }> {
    return api.patch<{ updated: number }>('/processes/bulk/status', { ids, status })
  },

  async bulkDelete(ids: string[]): Promise<{ deleted: number }> {
    return api.post<{ deleted: number }>('/processes/bulk/delete', { ids })
  },

  async listByLine(lineId: string): Promise<ApiProcess[]> {
    return api.get<ApiProcess[]>(`/lines/${lineId}/processes`)
  },

  async importProcesses(
    lineId: string,
    stationId: string,
    payload: ImportProcessesPayload,
  ): Promise<ApiProcess[]> {
    return api.post<ApiProcess[]>(
      `/lines/${lineId}/stations/${stationId}/processes/import`,
      payload,
    )
  },
}
