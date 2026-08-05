import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auditService } from '@/services/audit.service'
import type { AuditType, AuditListParams } from '@/services/audit.service'

export interface AuditEntry {
  id: string
  action: string
  user: string
  target: string
  timestamp: string
  type: AuditType
}

export interface AuditMeta {
  total: number
  page: number
  limit: number
  totalPages: number
}

export const useAuditStore = defineStore('audit', () => {
  const auditLog = ref<AuditEntry[]>([])
  const meta = ref<AuditMeta>({ total: 0, page: 1, limit: 25, totalPages: 1 })
  const typeCounts = ref<Record<string, number>>({})

  async function fetchAuditLog(params: AuditListParams = {}): Promise<void> {
    const res = await auditService.list({ limit: 25, ...params })
    auditLog.value = res.data.map(e => ({
      id: e.id,
      type: e.type,
      action: e.action,
      target: e.target,
      user: e.performer?.name ?? e.performedBy,
      timestamp: e.createdAt,
    }))
    meta.value = res.meta as AuditMeta
  }

  async function fetchTypeCounts(): Promise<void> {
    try {
      const s = await auditService.stats()
      typeCounts.value = s.byType
    } catch {
      // stats endpoint optional
    }
  }

  return { auditLog, meta, typeCounts, fetchAuditLog, fetchTypeCounts }
})
