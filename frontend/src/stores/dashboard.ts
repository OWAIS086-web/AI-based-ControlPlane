import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/services/api'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DashboardLine {
  id:             string
  name:           string
  stationCount:   number
  processCount:   number
  missingCPCount: number
  managerId:      string | null
}

export interface DashboardActivity {
  id:          string
  type:        string
  action:      string
  target:      string
  performedBy: string
  metadata:    unknown
  createdAt:   string
}

export interface DashboardStats {
  totalStations:  number
  totalProcesses: number
  totalCarModels: number
  missingCPCount: number
  lines:          DashboardLine[]
  recentActivity: DashboardActivity[]
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useDashboardStore = defineStore('dashboard', () => {
  const stats   = ref<DashboardStats | null>(null)
  const loading = ref(false)
  const error   = ref<string | null>(null)

  async function fetchStats() {
    loading.value = true
    error.value   = null
    try {
      stats.value = await api.get<DashboardStats>('/dashboard/stats')
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, error, fetchStats }
})