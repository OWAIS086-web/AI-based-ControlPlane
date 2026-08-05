import { api } from './api'

export interface ApiToolRequest {
  id: string
  reportedToolId: string
  toolDbId: string | null
  faultyToolRef: string | null
  typeId: string
  typeName: string
  workerId: string | null
  workerName: string | null
  workerExternalId: string | null
  reporterName: string
  notes: string | null
  status: 'pending' | 'in_review' | 'resolved'
  replacementToolId: string | null
  replacementToolRef: string | null
  resolvedNote: string | null
  resolvedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface ApiToolRequestList {
  requests: ApiToolRequest[]
  total: number
}

export const toolRequestsService = {
  list(params?: { status?: string; page?: number; limit?: number }): Promise<ApiToolRequestList> {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.page)   qs.set('page',   String(params.page))
    if (params?.limit)  qs.set('limit',  String(params.limit))
    const q = qs.toString()
    return api.get<ApiToolRequestList>(`/tool-requests${q ? '?' + q : ''}`)
  },

  get(id: string): Promise<ApiToolRequest> {
    return api.get<ApiToolRequest>(`/tool-requests/${id}`)
  },

  create(body: {
    reportedToolId: string
    typeId: string
    workerId?: string | null
    notes?: string | null
  }): Promise<ApiToolRequest> {
    return api.post<ApiToolRequest>('/tool-requests', body)
  },

  markFaulty(id: string, note?: string): Promise<ApiToolRequest> {
    return api.post<ApiToolRequest>(`/tool-requests/${id}/mark-faulty`, { note })
  },

  resolve(id: string, body: { replacementToolId?: string | null; note?: string | null }): Promise<ApiToolRequest> {
    return api.post<ApiToolRequest>(`/tool-requests/${id}/resolve`, body)
  },
}
