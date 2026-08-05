import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stationsService } from '@/services/stations.service'
import { processesService } from '@/services/processes.service'
import { versionsService } from '@/services/versions.service'
import { useLinesStore } from '@/stores/lines'
import type { ApiStation } from '@/services/stations.service'
import type { ApiProcess } from '@/services/processes.service'
import type { ApiProcessVersion } from '@/services/versions.service'
import type { ApiCarModel } from '@/services/carModels.service'

// ─── Store-friendly types ─────────────────────────────────────────────────────
// These are the shapes views consume. They differ from raw API types in that
// fileSize is formatted as a string, diff fields are renamed, etc.

export interface DiffRow {
  type: 'cell' | 'shape'
  row: string
  field: string
  old: string
  newVal: string
}

export interface ProcessVersion {
  id: string
  version: string
  fileName: string | null
  uploadedBy: string
  uploadedAt: string
  commitMessage: string
  changes: number
  shapeAdded: number
  shapeRemoved: number
  fileSize: string
  fileUrl: string
  diffRows: DiffRow[]
  extractedData: any
}

export interface Process {
  id: string
  name: string
  code: string
  extractedCode: string | null
  carModelId: string
  carModel: ApiCarModel | null
  status: 'active' | 'archived'
  hasMissingCP: boolean
  versionCount: number
  versions: ProcessVersion[]
  latestVersion: ProcessVersion | null
  stationId: string
  stationName: string
  lineId: string
  workerId: string | null
  workerName: string | null
  aiStatus: 'idle' | 'ai_running' | 'completed' | 'failed'
}

export interface Station {
  id: string
  name: string
  lineId: string
  processes: Process[]
}

// ─── Mappers ──────────────────────────────────────────────────────────────────

function parseShapeName(s: string): { field: string; value: string } {
  const idx = s.indexOf(': ')
  return idx === -1
    ? { field: 'Shape', value: s }
    : { field: s.slice(0, idx), value: s.slice(idx + 2) }
}

function mapVersion(v: ApiProcessVersion): ProcessVersion {
  const rows: DiffRow[] = []
  let shapeAdded = 0
  let shapeRemoved = 0

  try {
    const parsed: import('@/services/versions.service').ApiDiff =
      typeof v.diff === 'string' ? JSON.parse(v.diff) : v.diff

    for (const sheet of parsed?.sheets ?? []) {
      const cc = sheet.cell_changes
      for (const [cell, ch] of Object.entries(cc?.modified ?? {}))
        rows.push({ type: 'cell', row: sheet.sheet_name, field: cell, old: ch.previous, newVal: ch.current })
      for (const [cell, ch] of Object.entries(cc?.added ?? {}))
        rows.push({ type: 'cell', row: sheet.sheet_name, field: cell, old: '', newVal: ch.value })
      for (const [cell, ch] of Object.entries(cc?.removed ?? {}))
        rows.push({ type: 'cell', row: sheet.sheet_name, field: cell, old: ch.value, newVal: '' })

      for (const s of sheet.shape_changes?.added ?? []) {
        const { field, value } = parseShapeName(s)
        rows.push({ type: 'shape', row: sheet.sheet_name, field, old: '', newVal: value })
        shapeAdded++
      }
      for (const s of sheet.shape_changes?.removed ?? []) {
        const { field, value } = parseShapeName(s)
        rows.push({ type: 'shape', row: sheet.sheet_name, field, old: value, newVal: '' })
        shapeRemoved++
      }
    }
  } catch { /* leave rows empty */ }

  return {
    id: v.id,
    version: v.version,
    fileName: v.fileName ?? null,
    uploadedBy: v.uploader?.name ?? v.uploadedBy,
    uploadedAt: v.createdAt,
    commitMessage: v.commitMessage,
    changes: v.changes,
    shapeAdded,
    shapeRemoved,
    fileSize: v.fileSize ? `${(v.fileSize / (1024 * 1024)).toFixed(1)} MB` : '—',
    fileUrl: v.fileUrl ?? '',
    diffRows: rows,
    extractedData: v.extractedData,
  }
}

function mapProcess(p: ApiProcess, stationName: string): Process {
  return {
    id: p.id,
    name: p.name,
    code: p.code,
    extractedCode: p.extractedCode ?? null,
    carModelId: p.carModelId,
    carModel: p.carModel ?? null,
    status: p.status,
    hasMissingCP: p.hasMissingCp || !p.latestVersion,
    versionCount: p.versionCount,
    versions: [],
    latestVersion: p.latestVersion ? mapVersion(p.latestVersion) : null,
    stationId: p.stationId,
    stationName,
    lineId: p.lineId,
    workerId: p.workerId ?? null,
    workerName: p.workerName ?? null,
    aiStatus: (p.aiStatus ?? 'idle') as Process['aiStatus'],
  }
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useStationsStore = defineStore('stations', () => {
  const stations    = ref<Record<string, Station[]>>({})
  const loadedLines = ref<Set<string>>(new Set())

  const allProcesses = computed(() => {
    const linesStore = useLinesStore()
    const result: (Process & { lineName: string; lineColor: string })[] = []
    for (const [lineId, stns] of Object.entries(stations.value)) {
      const line = linesStore.lines.find(l => l.id === lineId)
      stns.forEach(s => {
        s.processes.forEach(p => result.push({
          ...p,
          lineName: line?.name ?? lineId,
          lineColor: line?.color ?? '#6366F1',
        }))
      })
    }
    return result
  })

  // ─── Fetch ──────────────────────────────────────────────────────────────────

  async function fetchStations(lineId: string): Promise<void> {
    const [stnRes, allProcs] = await Promise.all([
      stationsService.list(lineId, { limit: 100 }),
      processesService.listByLine(lineId),
    ])

    const processesByStation: Record<string, Process[]> = {}
    for (const s of stnRes.data) processesByStation[s.id] = []

    for (const p of allProcs) {
      const stn = stnRes.data.find(s => s.id === p.stationId)
      ;(processesByStation[p.stationId] ??= []).push(mapProcess(p, stn?.name ?? ''))
    }

    stations.value = {
      ...stations.value,
      [lineId]: stnRes.data.map((s: ApiStation) => ({
        id: s.id,
        name: s.name,
        lineId,
        processes: processesByStation[s.id] ?? [],
      })),
    }
    loadedLines.value.add(lineId)
  }

  async function fetchAllProcesses(): Promise<void> {
    const allProcs = await processesService.listAll()
    const grouped: Record<string, Record<string, Process[]>> = {}

    for (const p of allProcs) {
      const stn = findStation(p.stationId)
      ;((grouped[p.lineId] ??= {})[p.stationId] ??= []).push(mapProcess(p, stn?.name ?? p.stationId))
    }

    for (const [lineId, byStation] of Object.entries(grouped)) {
      stations.value = {
        ...stations.value,
        [lineId]: Object.entries(byStation).map(([stnId, procs]) => ({
          id: stnId,
          name: procs[0]?.stationName ?? stnId,
          lineId,
          processes: procs,
        })),
      }
    }
  }

  async function fetchProcessVersions(processId: string): Promise<ProcessVersion[]> {
    const res = await versionsService.list(processId, { limit: 100 })
    const versions = res.data.map(mapVersion)
    console.log('Fetched versions for process', processId, versions)

    for (const lineId of Object.keys(stations.value)) {
      stations.value[lineId] = stations.value[lineId].map(s => ({
        ...s,
        processes: s.processes.map(p =>
          p.id === processId ? {
            ...p,
            versions,
            versionCount: versions.length,
            latestVersion: versions[0] ?? null,
            hasMissingCP: versions.length === 0,
          } : p,
        ),
      }))
    }
    return versions
  }

  // ─── Mutations ───────────────────────────────────────────────────────────────

  async function addStation(lineId: string, name: string): Promise<string> {
    const stn = await stationsService.create(lineId, { name })
    const newStation: Station = { id: stn.id, name: stn.name, lineId, processes: [] }
    stations.value = {
      ...stations.value,
      [lineId]: [...(stations.value[lineId] ?? []), newStation],
    }
    return stn.id
  }

  async function renameStation(lineId: string, stationId: string, name: string): Promise<void> {
    const stn = await stationsService.update(lineId, stationId, { name })
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id === stationId ? { ...s, name: stn.name } : s
      ),
    }
  }

  async function deleteStation(lineId: string, stationId: string): Promise<void> {
    await stationsService.remove(lineId, stationId)
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).filter(s => s.id !== stationId),
    }
  }

  async function addProcess(
    lineId: string,
    stationId: string,
    name: string,
    carModelId: string,
  ): Promise<void> {
    const p = await processesService.create(lineId, stationId, { name, carModelId })
    const stn = findStation(stationId)
    const proc = mapProcess(p, stn?.name ?? '')
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id === stationId ? { ...s, processes: [...s.processes, proc] } : s,
      ),
    }
  }

  async function setProcessStatus(
    lineId: string,
    stationId: string,
    processId: string,
    status: 'active' | 'archived',
  ): Promise<void> {
    await processesService.setStatus(processId, { status })
    updateProcess(lineId, stationId, processId, p => ({ ...p, status }))
  }

  async function bulkSetProcessStatus(
    lineId: string,
    stationId: string,
    ids: string[],
    status: 'active' | 'archived',
  ): Promise<void> {
    await processesService.bulkSetStatus(ids, status)
    const idSet = new Set(ids)
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id !== stationId ? s : {
          ...s,
          processes: s.processes.map(p => idSet.has(p.id) ? { ...p, status } : p),
        },
      ),
    }
  }

  async function bulkDeleteProcesses(
    lineId: string,
    stationId: string,
    ids: string[],
  ): Promise<void> {
    await processesService.bulkDelete(ids)
    const idSet = new Set(ids)
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id !== stationId ? s : {
          ...s,
          processes: s.processes.filter(p => !idSet.has(p.id)),
        },
      ),
    }
  }

  async function deleteProcess(
    lineId: string,
    stationId: string,
    processId: string,
  ): Promise<void> {
    await processesService.delete(processId)
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id !== stationId ? s : {
          ...s,
          processes: s.processes.filter(p => p.id !== processId),
        },
      ),
    }
  }

  async function uploadVersion(
    lineId: string,
    stationId: string,
    processId: string,
    commitMessage: string,
    file: File,
  ): Promise<void> {
    const v = await versionsService.upload(processId, file, commitMessage)
    const newVersion = mapVersion(v)
    updateProcess(lineId, stationId, processId, p => ({
      ...p,
      versions: [newVersion, ...p.versions],
      latestVersion: newVersion,
      versionCount: p.versionCount + 1,
      hasMissingCP: false,
    }))
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────────

  function findStation(stationId: string): Station | undefined {
    for (const line of Object.values(stations.value)) {
      const found = line.find(s => s.id === stationId)
      if (found) return found
    }
  }

  function updateProcess(
    lineId: string,
    stationId: string,
    processId: string,
    updater: (p: Process) => Process,
  ) {
    stations.value = {
      ...stations.value,
      [lineId]: (stations.value[lineId] ?? []).map(s =>
        s.id !== stationId ? s : {
          ...s,
          processes: s.processes.map(p => p.id === processId ? updater(p) : p),
        },
      ),
    }
  }

  return {
    stations, allProcesses, loadedLines,
    fetchStations, fetchAllProcesses, fetchProcessVersions,
    addStation, renameStation, deleteStation,
    addProcess, setProcessStatus, deleteProcess, uploadVersion,
    bulkSetProcessStatus, bulkDeleteProcesses,
  }
})
