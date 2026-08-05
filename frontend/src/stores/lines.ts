import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { linesService } from '@/services/lines.service'
import { lineTypesService } from '@/services/lineTypes.service'
import type { ApiLine } from '@/services/lines.service'
import type { ApiLineType } from '@/services/lineTypes.service'

// ─── Public types ─────────────────────────────────────────────────────────────

export interface Line {
  id: string
  name: string
  icon: string
  color: string
  stationCount: number
  lineTypeId: string | null
  order: number
  managerId: string | null
}

export interface LineType {
  id: string
  name: string
  icon: string
  color: string
  order: number
}

export interface LineTypeWithLines extends LineType {
  lines: Line[]
}

// ─── Mappers ──────────────────────────────────────────────────────────────────

function mapLine(l: ApiLine): Line {
  return {
    id: l.id,
    name: l.name,
    icon: l.icon,
    color: l.color,
    stationCount: l.stationCount,
    lineTypeId: l.lineTypeId ?? null,
    order: l.order ?? 0,
    managerId: l.managerId ?? null,
  }
}

function mapType(t: ApiLineType): LineType {
  return { id: t.id, name: t.name, icon: t.icon, color: t.color, order: t.order }
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useLinesStore = defineStore('lines', () => {
  const lines     = ref<Line[]>([])
  const lineTypes = ref<LineType[]>([])

  // Lines grouped by type, sorted by type.order then line.order
  const linesByType = computed((): LineTypeWithLines[] =>
    [...lineTypes.value]
      .sort((a, b) => a.order - b.order)
      .map(type => ({
        ...type,
        lines: lines.value
          .filter(l => l.lineTypeId === type.id)
          .sort((a, b) => a.order - b.order),
      })),
  )

  // Lines with no type assigned
  const untypedLines = computed((): Line[] =>
    lines.value.filter(l => !l.lineTypeId).sort((a, b) => a.order - b.order),
  )

  // Flat lines sorted by their type order then line order (used by sidebar)
  const sortedLines = computed((): Line[] => {
    const result: Line[] = []
    for (const group of linesByType.value) result.push(...group.lines)
    // Append lines with no type at the end
    const untyped = lines.value.filter(l => !l.lineTypeId)
    result.push(...untyped)
    return result
  })

  async function fetchLines(): Promise<void> {
    const apiLines = await linesService.list()
    lines.value = apiLines.map(mapLine)
  }

  async function fetchLineTypes(): Promise<void> {
    const apiTypes = await lineTypesService.list()
    lineTypes.value = apiTypes.map(mapType)
  }

  async function fetchAll(): Promise<void> {
    const [apiLines, apiTypes] = await Promise.all([linesService.list(), lineTypesService.list()])
    lines.value     = apiLines.map(mapLine)
    lineTypes.value = apiTypes.map(mapType)
  }

  // ── Line mutations ──────────────────────────────────────────────────────────

  async function createLine(payload: {
    name: string
    icon: string
    color: string
    lineTypeId: string | null
  }): Promise<Line> {
    const created = await linesService.create(payload)
    const line = mapLine(created)
    lines.value = [...lines.value, line]
    return line
  }

  async function updateLine(id: string, payload: {
    name?: string
    icon?: string
    color?: string
    lineTypeId?: string | null
  }): Promise<Line> {
    const updated = await linesService.update(id, payload)
    const line = mapLine(updated)
    lines.value = lines.value.map(l => l.id === id ? line : l)
    return line
  }

  async function deleteLine(id: string): Promise<void> {
    await linesService.remove(id)
    lines.value = lines.value.filter(l => l.id !== id)
  }

  async function reorderLines(ids: string[]): Promise<void> {
    const updated = await linesService.reorder(ids)
    lines.value = updated.map(mapLine)
  }

  // ── LineType mutations ──────────────────────────────────────────────────────

  async function createLineType(payload: {
    name: string
    icon: string
    color: string
  }): Promise<LineType> {
    const created = await lineTypesService.create(payload)
    const lt = mapType(created)
    lineTypes.value = [...lineTypes.value, lt]
    return lt
  }

  async function updateLineType(id: string, payload: {
    name?: string
    icon?: string
    color?: string
  }): Promise<LineType> {
    const updated = await lineTypesService.update(id, payload)
    const lt = mapType(updated)
    lineTypes.value = lineTypes.value.map(t => t.id === id ? lt : t)
    return lt
  }

  async function deleteLineType(id: string): Promise<void> {
    await lineTypesService.remove(id)
    lineTypes.value = lineTypes.value.filter(t => t.id !== id)
    // Unlink lines that belonged to this type
    lines.value = lines.value.map(l => l.lineTypeId === id ? { ...l, lineTypeId: null } : l)
  }

  async function reorderLineTypes(ids: string[]): Promise<void> {
    const updated = await lineTypesService.reorder(ids)
    lineTypes.value = updated.map(mapType)
  }

  return {
    lines,
    lineTypes,
    linesByType,
    untypedLines,
    sortedLines,
    fetchLines,
    fetchLineTypes,
    fetchAll,
    createLine,
    updateLine,
    deleteLine,
    reorderLines,
    createLineType,
    updateLineType,
    deleteLineType,
    reorderLineTypes,
  }
})
