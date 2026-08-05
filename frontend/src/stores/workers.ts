import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workersService } from '@/services/workers.service'
import type { ApiWorker, ApiWorkerAssignment } from '@/services/workers.service'

export interface Worker {
  id: string
  name: string
  workerId: string
  assignedCount: number
  assignments: ApiWorkerAssignment[]
  createdAt: string
  updatedAt: string
}

function mapWorker(w: ApiWorker): Worker {
  return {
    id: w.id,
    name: w.name,
    workerId: w.workerId,
    assignedCount: w.assignedCount,
    assignments: w.assignments ?? [],
    createdAt: w.createdAt,
    updatedAt: w.updatedAt,
  }
}

export const useWorkersStore = defineStore('workers', () => {
  const workers      = ref<Worker[]>([])
  const total        = ref(0)
  const page         = ref(1)
  const limit        = ref(50)
  const searchQuery  = ref('')

  async function fetchWorkers(params: { search?: string; page?: number; limit?: number } = {}) {
    const res = await workersService.list({
      search: (params.search ?? searchQuery.value) || undefined,
      page:   params.page  ?? page.value,
      limit:  params.limit ?? limit.value,
    })
    workers.value = res.data.map(mapWorker)
    total.value   = res.meta.total
    if (params.page  != null) page.value  = params.page
    if (params.limit != null) limit.value = params.limit
    if (params.search !== undefined) searchQuery.value = params.search ?? ''
  }

  /** Flat list for dropdowns — not paginated */
  async function fetchAll(): Promise<Worker[]> {
    const list = await workersService.listAll()
    return list.map(mapWorker)
  }

  async function createWorker(name: string, workerId: string): Promise<Worker> {
    const w = await workersService.create({ name, workerId })
    const mapped = mapWorker(w)
    workers.value = [...workers.value, mapped]
    total.value   += 1
    return mapped
  }

  async function updateWorker(id: string, payload: { name?: string; workerId?: string }): Promise<Worker> {
    const w = await workersService.update(id, payload)
    const mapped = mapWorker(w)
    workers.value = workers.value.map(x => x.id === id ? mapped : x)
    return mapped
  }

  async function deleteWorker(id: string): Promise<void> {
    await workersService.remove(id)
    workers.value = workers.value.filter(x => x.id !== id)
    total.value   = Math.max(0, total.value - 1)
  }

  async function assignWorker(processIds: string[], workerId: string | null): Promise<void> {
    await workersService.assign(processIds, workerId)
  }

  return {
    workers,
    total,
    page,
    limit,
    searchQuery,
    fetchWorkers,
    fetchAll,
    createWorker,
    updateWorker,
    deleteWorker,
    assignWorker,
  }
})
