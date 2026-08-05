import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'
import type { ApiUser } from '@/services/auth.service'

// ─── Types ───────────────────────────────────────────────────────────────────

export type AuditType = 'upload' | 'user' | 'station' | 'archive' | 'migrate' | 'model'

export interface ApiAuditEntry {
  id: string
  type: AuditType
  action: string
  target: string
  performedBy: string      // User ID
  performer?: ApiUser
  metadata: Record<string, unknown>
  createdAt: string
}

export interface AuditStats {
  total: number
  byType: Record<AuditType, number>
}

export interface AuditListParams {
  type?: AuditType | 'all'
  performedBy?: string
  search?: string
  from?: string            // ISO date
  to?: string              // ISO date
  page?: number
  limit?: number
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const auditService = {
  async list(params: AuditListParams = {}): Promise<PaginatedResponse<ApiAuditEntry>> {
    const qs = new URLSearchParams()
    if (params.type && params.type !== 'all') qs.set('type',        params.type)
    if (params.performedBy)                   qs.set('performedBy', params.performedBy)
    if (params.search)                        qs.set('search',      params.search)
    if (params.from)                          qs.set('from',        params.from)
    if (params.to)                            qs.set('to',          params.to)
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiAuditEntry>>(`/audit?${qs}`)
  },

  async stats(): Promise<AuditStats> {
    return api.get<AuditStats>('/audit/stats')
  },
}
