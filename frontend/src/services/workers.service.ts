import { api } from './api'

export interface ApiWorkerAssignment {
  processId: string
  processName: string
  processCode: string
  processStatus: string
  carModelId: string
  carModelName: string
  lineId: string
  stationId: string
}

export interface ApiWorker {
  id: string
  name: string
  workerId: string
  assignedCount: number
  assignments: ApiWorkerAssignment[]
  createdAt: string
  updatedAt: string
}

export interface WorkerListResponse {
  data: ApiWorker[]
  meta: {
    total: number
    page: number
    limit: number
    totalPages: number
  }
}

export const workersService = {
  list(params: { search?: string; page?: number; limit?: number } = {}): Promise<WorkerListResponse> {
    const query = new URLSearchParams()
    if (params.search)        query.set('search', params.search)
    if (params.page != null)  query.set('page',   String(params.page))
    if (params.limit != null) query.set('limit',  String(params.limit))
    const qs = query.toString()
    return api.get<WorkerListResponse>(`/workers${qs ? '?' + qs : ''}`)
  },

  listAll(): Promise<ApiWorker[]> {
    return api.get<ApiWorker[]>('/workers/all')
  },

  get(id: string): Promise<ApiWorker> {
    return api.get<ApiWorker>(`/workers/${id}`)
  },

  create(payload: { name: string; workerId: string }): Promise<ApiWorker> {
    return api.post<ApiWorker>('/workers', payload)
  },

  update(id: string, payload: { name?: string; workerId?: string }): Promise<ApiWorker> {
    return api.patch<ApiWorker>(`/workers/${id}`, payload)
  },

  remove(id: string): Promise<void> {
    return api.delete(`/workers/${id}`)
  },

  /** Assign (or unassign) a worker to one or more processes.
   *  Pass workerId = null to remove assignments. */
  assign(processIds: string[], workerId: string | null): Promise<void> {
    return api.post<void>('/workers/assign', { processIds, workerId })
  },
}
