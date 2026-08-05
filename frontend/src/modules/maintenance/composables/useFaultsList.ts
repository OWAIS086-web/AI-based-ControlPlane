import { ref, reactive } from 'vue'
import { maintenanceFaultService, type FaultRecord } from '@/services/maintenanceApi'

export function useFaultsList() {
  const faults     = ref<FaultRecord[]>([])
  const loading    = ref(false)
  const total      = ref(0)
  const page       = ref(1)
  const totalPages = ref(1)
  const PAGE_SIZE  = 20

  const filters = reactive({ status: '', severity: '' })

  async function fetchFaults() {
    loading.value = true
    try {
      const params: Record<string, string | number> = { page: page.value, page_size: PAGE_SIZE }
      if (filters.status)   params.status   = filters.status
      if (filters.severity) params.severity = filters.severity
      const res = await maintenanceFaultService.list(params)
      faults.value     = res.data
      total.value      = res.meta.total
      totalPages.value = res.meta.totalPages
    } finally {
      loading.value = false
    }
  }

  function applyFilters() { page.value = 1; fetchFaults() }
  function onPage(p: number) { page.value = p; fetchFaults() }
  function clearFilters() { filters.status = ''; filters.severity = ''; applyFilters() }

  return { faults, loading, total, page, totalPages, filters, fetchFaults, applyFilters, onPage, clearFilters }
}
