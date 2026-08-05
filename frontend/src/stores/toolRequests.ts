import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toolRequestsService } from '@/services/toolRequests.service'
import type { ApiToolRequest } from '@/services/toolRequests.service'

export type { ApiToolRequest }

export const useToolRequestsStore = defineStore('toolRequests', () => {
  const requests = ref<ApiToolRequest[]>([])
  const total    = ref(0)
  const page     = ref(1)
  const limit    = ref(50)

  async function fetchRequests(params?: { status?: string; page?: number; limit?: number }) {
    if (params?.page)  page.value  = params.page
    if (params?.limit) limit.value = params.limit
    const res = await toolRequestsService.list({
      status: params?.status,
      page:   page.value,
      limit:  limit.value,
    })
    requests.value = res.requests
    total.value    = res.total
    return res
  }

  async function createRequest(body: Parameters<typeof toolRequestsService.create>[0]) {
    const r = await toolRequestsService.create(body)
    requests.value.unshift(r)
    total.value++
    return r
  }

  async function markFaulty(id: string, note?: string) {
    const updated = await toolRequestsService.markFaulty(id, note)
    _replace(updated)
    return updated
  }

  async function resolve(id: string, body: Parameters<typeof toolRequestsService.resolve>[1]) {
    const updated = await toolRequestsService.resolve(id, body)
    _replace(updated)
    return updated
  }

  function _replace(r: ApiToolRequest) {
    const idx = requests.value.findIndex(x => x.id === r.id)
    if (idx !== -1) requests.value[idx] = r
  }

  return { requests, total, page, limit, fetchRequests, createRequest, markFaulty, resolve }
})
