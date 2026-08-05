import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getAccessToken, tryRefresh } from '@/services/api'

const BASE_URL = '/api/v1'
const MAX_CONCURRENCY = 3

export interface UploadResponse {
  status: 'created' | 'matched' | 'rejected'
  message: string
  extractedCode?: string
  process?: { id: string; name: string; code: string; [key: string]: unknown }
  version?: { id: string; version: string; [key: string]: unknown }
}

export interface FileEntry {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'created' | 'matched' | 'rejected' | 'error' | 'cancelled'
  progress: number   // 0–99 while uploading, 100 on completion, -1 = indeterminate
  lineId: string
  stationId: string
  carModelId: string
  response?: UploadResponse
  error?: string
  abortController?: AbortController
}

export const useUploadsStore = defineStore('uploads', () => {
  const queue = ref<FileEntry[]>([])

  const activeCount  = computed(() => queue.value.filter(e => e.status === 'uploading').length)
  const pendingCount = computed(() => queue.value.filter(e => e.status === 'pending').length)
  const doneCount    = computed(() => queue.value.filter(e => ['created', 'matched', 'rejected'].includes(e.status)).length)
  const errorCount   = computed(() => queue.value.filter(e => e.status === 'error').length)
  const totalCount   = computed(() => queue.value.filter(e => e.status !== 'cancelled').length)

  // ── Internals ──────────────────────────────────────────────────────────────

  function updateEntry(id: string, patch: Partial<FileEntry>) {
    const idx = queue.value.findIndex(e => e.id === id)
    if (idx !== -1) queue.value[idx] = { ...queue.value[idx], ...patch }
  }

  function tickPool() {
    let active = queue.value.filter(e => e.status === 'uploading').length
    while (active < MAX_CONCURRENCY) {
      const next = queue.value.find(e => e.status === 'pending')
      if (!next) break
      startUpload(next.id)
      active++
    }
  }

  function startUpload(entryId: string, isRetryAfterRefresh = false) {
    const entry = queue.value.find(e => e.id === entryId)
    if (!entry) return

    const ctrl = new AbortController()
    updateEntry(entryId, { status: 'uploading', progress: 0, abortController: ctrl })

    const formData = new FormData()
    formData.append('file', entry.file)
    formData.append('carModelId', entry.carModelId)
    formData.append('commitMessage', 'Auto-uploaded')

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE_URL}/lines/${entry.lineId}/stations/${entry.stationId}/excel-upload`)

    const token = getAccessToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (e: ProgressEvent) => {
      const cur = queue.value.find(en => en.id === entryId)
      if (!cur || cur.status === 'cancelled') return
      updateEntry(entryId, {
        progress: e.lengthComputable
          ? Math.min(Math.round((e.loaded / e.total) * 100), 99)
          : -1,
      })
    }

    xhr.onload = () => {
      const cur = queue.value.find(en => en.id === entryId)
      if (!cur || cur.status === 'cancelled') { tickPool(); return }

      // Token expired — try refresh once then retry the upload
      if (xhr.status === 401 && !isRetryAfterRefresh) {
        tryRefresh().then(refreshed => {
          if (refreshed) {
            startUpload(entryId, true)
          } else {
            updateEntry(entryId, { status: 'error', progress: 0, error: 'Session expired — please log in again' })
            tickPool()
          }
        })
        return
      }

      try {
        const res = JSON.parse(xhr.responseText)
        if (xhr.status >= 200 && xhr.status < 300) {
          updateEntry(entryId, {
            progress: 100,
            status: res.status as FileEntry['status'],
            response: res as UploadResponse,
          })
        } else {
          updateEntry(entryId, {
            status: 'error',
            progress: 0,
            error: res.message ?? res.detail ?? `Upload failed (${xhr.status})`,
          })
        }
      } catch {
        updateEntry(entryId, { status: 'error', progress: 0, error: 'Invalid server response' })
      }
      tickPool()
    }

    xhr.onerror = () => {
      const cur = queue.value.find(en => en.id === entryId)
      if (!cur || cur.status === 'cancelled') { tickPool(); return }
      updateEntry(entryId, { status: 'error', progress: 0, error: 'Network failure' })
      tickPool()
    }

    ctrl.signal.addEventListener('abort', () => xhr.abort())
    xhr.send(formData)
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /** Append files to the queue. Returns the count of silently-skipped duplicates.
   *  force=true skips all dupe checks (used after user confirms overwrite). */
  function appendToQueue(
    files: FileList | File[],
    lineId: string,
    stationId: string,
    carModelId: string,
    force = false,
  ): number {
    const arr = Array.from(files)
    const newEntries: FileEntry[] = []
    let dupeCount = 0

    for (const file of arr) {
      if (!force) {
        const isDupe = queue.value.some(
          e => e.file.name === file.name && e.file.size === file.size && e.file.lastModified === file.lastModified,
        )
        if (isDupe) { dupeCount++; continue }
      }
      const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)
      newEntries.push({ id, file, status: 'pending', progress: 0, lineId, stationId, carModelId })
    }

    queue.value.push(...newEntries)
    if (newEntries.length) tickPool()
    return dupeCount
  }

  /** Cancel uploading entries and remove all pending entries. */
  function cancelRemaining() {
    queue.value = queue.value.flatMap(entry => {
      if (entry.status === 'uploading') {
        entry.abortController?.abort()
        return [{ ...entry, status: 'cancelled' as const, progress: 0 }]
      }
      if (entry.status === 'pending') return []
      return [entry]
    })
  }

  /** Re-queue all error entries as pending. */
  function retryFailed() {
    queue.value = queue.value.map(entry =>
      entry.status === 'error'
        ? { ...entry, status: 'pending' as const, progress: 0, error: undefined, response: undefined }
        : entry,
    )
    tickPool()
  }

  /** Re-queue a single error entry. */
  function retryEntry(id: string) {
    queue.value = queue.value.map(entry =>
      entry.id === id && entry.status === 'error'
        ? { ...entry, status: 'pending' as const, progress: 0, error: undefined, response: undefined }
        : entry,
    )
    tickPool()
  }

  /** Cancel/abort an entry and remove it from the queue. */
  function removeEntry(id: string) {
    const entry = queue.value.find(e => e.id === id)
    if (entry?.status === 'uploading') entry.abortController?.abort()
    queue.value = queue.value.filter(e => e.id !== id)
    tickPool()
  }

  return {
    queue,
    activeCount,
    pendingCount,
    doneCount,
    errorCount,
    totalCount,
    appendToQueue,
    cancelRemaining,
    retryFailed,
    retryEntry,
    removeEntry,
  }
})
