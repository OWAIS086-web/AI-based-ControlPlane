import { defineStore } from 'pinia'
import { ref } from 'vue'
import { migrationsService } from '@/services/migrations.service'
import type { MigrationListParams } from '@/services/migrations.service'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useAuthStore } from '@/stores/auth'

export interface MigrationRecord {
  id: string
  from: string
  to: string
  procs: string[]
  by: string
  date: string
  status: 'pending' | 'completed' | 'failed'
  fromLineId: string
  fromStationId: string
  toLineId: string
  toStationId: string
}

export interface MigrationMeta {
  total: number
  page: number
  limit: number
  totalPages: number
}

export const useMigrationsStore = defineStore('migrations', () => {
  const migrationHistory = ref<MigrationRecord[]>([])
  const meta = ref<MigrationMeta>({ total: 0, page: 1, limit: 20, totalPages: 1 })

  async function fetchMigrations(params: MigrationListParams = {}): Promise<void> {
    const stationsStore = useStationsStore()
    const res = await migrationsService.list({ limit: 20, ...params })

    migrationHistory.value = res.data.map(m => {
      const fromStn  = (stationsStore.stations[m.fromLineId] ?? []).find(s => s.id === m.fromStationId)
      const toStn    = (stationsStore.stations[m.toLineId]   ?? []).find(s => s.id === m.toStationId)
      const linesStore = useLinesStore()
      const fromLine = linesStore.lines.find(l => l.id === m.fromLineId)?.name ?? m.fromLineId
      const toLine   = linesStore.lines.find(l => l.id === m.toLineId)?.name   ?? m.toLineId

      return {
        id: m.id,
        from: `${fromLine} / ${fromStn?.name ?? m.fromStationId}`,
        to:   `${toLine} / ${toStn?.name ?? m.toStationId}`,
        procs: m.processNames,
        by: m.performedByName,
        date: m.createdAt.split('T')[0],
        status: m.status,
        fromLineId: m.fromLineId,
        fromStationId: m.fromStationId,
        toLineId: m.toLineId,
        toStationId: m.toStationId,
      }
    })
    meta.value = res.meta as MigrationMeta
  }

  async function migrateProcesses(
    fromLine: string,
    fromStnId: string,
    toLine: string,
    toStnId: string,
    processIds: string[],
  ): Promise<void> {
    const stationsStore = useStationsStore()
    const authStore     = useAuthStore()

    const fromStn = (stationsStore.stations[fromLine] ?? []).find(s => s.id === fromStnId)
    const toStn   = (stationsStore.stations[toLine]   ?? []).find(s => s.id === toStnId)

    const result = await migrationsService.create({
      fromLineId: fromLine,
      fromStationId: fromStnId,
      toLineId: toLine,
      toStationId: toStnId,
      processIds,
    })

    const processNames = processIds.map(
      id => fromStn?.processes.find(p => p.id === id)?.name ?? id,
    )

    const linesStore   = useLinesStore()
    const fromLineName = linesStore.lines.find(l => l.id === fromLine)?.name ?? fromLine
    const toLineName   = linesStore.lines.find(l => l.id === toLine)?.name   ?? toLine

    migrationHistory.value.unshift({
      id: result.id,
      from: `${fromLineName} / ${fromStn?.name ?? fromStnId}`,
      to:   `${toLineName} / ${toStn?.name ?? toStnId}`,
      procs: processNames,
      by: authStore.currentUser?.name ?? 'Unknown',
      date: new Date().toISOString().split('T')[0],
      status: result.status,
      fromLineId: fromLine,
      fromStationId: fromStnId,
      toLineId: toLine,
      toStationId: toStnId,
    })
  }

  return { migrationHistory, meta, fetchMigrations, migrateProcesses }
})
