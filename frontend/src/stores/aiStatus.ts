import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAccessToken } from '@/services/api'

export type AIStatus = 'idle' | 'ai_running' | 'completed' | 'failed'

export const useAIStatusStore = defineStore('aiStatus', () => {
  // processId → current AI status
  const statuses = ref<Record<string, AIStatus>>({})
  let source: EventSource | null = null

  function setStatus(processId: string, status: AIStatus) {
    statuses.value[processId] = status
  }

  function getStatus(processId: string): AIStatus {
    return statuses.value[processId] ?? 'idle'
  }

  /** Seed initial statuses from already-loaded process objects. */
  function seedFromProcesses(processes: { id: string; aiStatus?: AIStatus }[]) {
    for (const p of processes) {
      if (p.aiStatus && p.aiStatus !== 'idle') {
        statuses.value[p.id] = p.aiStatus
      }
    }
  }

  /** Open a single shared SSE connection. Safe to call multiple times — no-op if already open. */
  function connect() {
    if (source && source.readyState !== EventSource.CLOSED) return

    const token = getAccessToken()
    const url = `/api/v1/processes/ai-status/stream${token ? `?token=${token}` : ''}`
    source = new EventSource(url)

    source.addEventListener('ai.status', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as { processId: string; status: AIStatus }
        statuses.value[data.processId] = data.status
      } catch { /* ignore malformed */ }
    })

    source.onerror = () => {
      // Browser auto-reconnects EventSource — just log
      console.warn('[AIStatus] SSE connection lost, browser will retry')
    }
  }

  function disconnect() {
    source?.close()
    source = null
  }

  return { statuses, getStatus, setStatus, seedFromProcesses, connect, disconnect }
})
