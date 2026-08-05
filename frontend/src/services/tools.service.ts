import { api } from './api'
import type { PaginatedResponse } from './api'

export interface ApiToolType {
  id: string
  name: string
  maxPerWorker: number
  toolCount: number
  createdAt: string
  updatedAt: string
}

export interface ApiToolEvent {
  id: string
  action: string
  workerId: string | null
  workerName: string | null
  processId: string | null
  processName: string | null
  note: string | null
  createdAt: string
}

export interface ApiTool {
  id: string
  toolId: string
  typeId: string
  typeName: string
  status: 'available' | 'assigned' | 'faulty' | 'in_repair'
  workerId: string | null
  workerName: string | null
  processId: string | null
  processName: string | null
  notes: string | null
  events: ApiToolEvent[]
  createdAt: string
  updatedAt: string
}

export const toolTypesService = {
  list(): Promise<ApiToolType[]> {
    return api.get<ApiToolType[]>('/tool-types')
  },
  create(payload: { name: string; maxPerWorker: number }): Promise<ApiToolType> {
    return api.post<ApiToolType>('/tool-types', payload)
  },
  update(id: string, payload: { name?: string; maxPerWorker?: number }): Promise<ApiToolType> {
    return api.patch<ApiToolType>(`/tool-types/${id}`, payload)
  },
  remove(id: string): Promise<void> {
    return api.delete(`/tool-types/${id}`)
  },
}

export const toolsService = {
  list(
    params: { search?: string; typeId?: string; status?: string; page?: number; limit?: number } = {},
  ): Promise<PaginatedResponse<ApiTool>> {
    const qs = new URLSearchParams()
    if (params.search) qs.set('search', params.search)
    if (params.typeId) qs.set('typeId', params.typeId)
    if (params.status) qs.set('status', params.status)
    if (params.page)   qs.set('page',   String(params.page))
    if (params.limit)  qs.set('limit',  String(params.limit))
    const q = qs.toString()
    return api.get<PaginatedResponse<ApiTool>>(`/tools${q ? '?' + q : ''}`)
  },
  listAll(params: { typeId?: string; status?: string } = {}): Promise<ApiTool[]> {
    const qs = new URLSearchParams()
    if (params.typeId) qs.set('typeId', params.typeId)
    if (params.status) qs.set('status', params.status)
    const q = qs.toString()
    return api.get<ApiTool[]>(`/tools/all${q ? '?' + q : ''}`)
  },
  get(id: string): Promise<ApiTool> {
    return api.get<ApiTool>(`/tools/${id}`)
  },
  create(payload: { toolId: string; typeId: string; notes?: string }): Promise<ApiTool> {
    return api.post<ApiTool>('/tools', payload)
  },
  update(id: string, payload: { toolId?: string; notes?: string }): Promise<ApiTool> {
    return api.patch<ApiTool>(`/tools/${id}`, payload)
  },
  remove(id: string): Promise<void> {
    return api.delete(`/tools/${id}`)
  },
  assign(
    id: string,
    payload: { workerId?: string | null; processId?: string | null },
  ): Promise<ApiTool> {
    return api.post<ApiTool>(`/tools/${id}/assign`, payload)
  },
  setStatus(id: string, payload: { status: string; note?: string }): Promise<ApiTool> {
    return api.post<ApiTool>(`/tools/${id}/status`, payload)
  },
}
