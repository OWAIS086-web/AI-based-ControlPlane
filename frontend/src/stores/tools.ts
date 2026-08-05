import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toolTypesService, toolsService } from '@/services/tools.service'
import type { ApiTool, ApiToolType } from '@/services/tools.service'

export type { ApiTool, ApiToolType }

export const useToolTypesStore = defineStore('toolTypes', () => {
  const types = ref<ApiToolType[]>([])

  async function fetchTypes() {
    types.value = await toolTypesService.list()
  }

  async function createType(name: string, maxPerWorker: number) {
    const t = await toolTypesService.create({ name, maxPerWorker })
    types.value = [...types.value, t]
    return t
  }

  async function updateType(id: string, payload: { name?: string; maxPerWorker?: number }) {
    const t = await toolTypesService.update(id, payload)
    types.value = types.value.map(x => (x.id === id ? t : x))
    return t
  }

  async function deleteType(id: string) {
    await toolTypesService.remove(id)
    types.value = types.value.filter(x => x.id !== id)
  }

  return { types, fetchTypes, createType, updateType, deleteType }
})

export const useToolsStore = defineStore('tools', () => {
  const tools = ref<ApiTool[]>([])
  const total = ref(0)
  const page  = ref(1)
  const limit = ref(50)

  async function fetchTools(
    params: { search?: string; typeId?: string; status?: string; page?: number; limit?: number } = {},
  ) {
    const res = await toolsService.list({
      search: params.search,
      typeId: params.typeId,
      status: params.status,
      page:   params.page  ?? page.value,
      limit:  params.limit ?? limit.value,
    })
    tools.value = res.data
    total.value = res.meta.total
    if (params.page  != null) page.value  = params.page
    if (params.limit != null) limit.value = params.limit
  }

  async function fetchAll(params: { typeId?: string; status?: string } = {}): Promise<ApiTool[]> {
    return toolsService.listAll(params)
  }

  async function createTool(payload: { toolId: string; typeId: string; notes?: string }) {
    const t = await toolsService.create(payload)
    tools.value = [...tools.value, t]
    total.value += 1
    return t
  }

  async function updateTool(id: string, payload: { toolId?: string; notes?: string }) {
    const t = await toolsService.update(id, payload)
    tools.value = tools.value.map(x => (x.id === id ? t : x))
    return t
  }

  async function deleteTool(id: string) {
    await toolsService.remove(id)
    tools.value = tools.value.filter(x => x.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  async function assignTool(
    id: string,
    payload: { workerId?: string | null; processId?: string | null },
  ) {
    const t = await toolsService.assign(id, payload)
    tools.value = tools.value.map(x => (x.id === id ? t : x))
    return t
  }

  async function setStatus(id: string, status: string, note?: string) {
    const t = await toolsService.setStatus(id, { status, note })
    tools.value = tools.value.map(x => (x.id === id ? t : x))
    return t
  }

  return {
    tools,
    total,
    page,
    limit,
    fetchTools,
    fetchAll,
    createTool,
    updateTool,
    deleteTool,
    assignTool,
    setStatus,
  }
})
