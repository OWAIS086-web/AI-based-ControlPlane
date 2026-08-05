<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToolsStore, useToolTypesStore } from '@/stores/tools'
import type { ApiTool } from '@/stores/tools'
import { useWorkersStore } from '@/stores/workers'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import type { Process } from '@/stores/stations'
import { useToast } from '@/composables/useToast'
import AppButton  from '@/components/ui/AppButton.vue'
import AppModal   from '@/components/ui/AppModal.vue'
import FormField  from '@/components/ui/FormField.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppInput   from '@/components/ui/AppInput.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import {
  HardHat, ClipboardList, Search, Wrench, ChevronDown,
  X, RefreshCw, Tag, User, Plus, Check, Car,
} from 'lucide-vue-next'

const toolsStore     = useToolsStore()
const toolTypesStore = useToolTypesStore()
const workersStore   = useWorkersStore()
const linesStore     = useLinesStore()
const stStore        = useStationsStore()
const { toast }      = useToast()

// ─── Resizable panel ──────────────────────────────────────────────────────────
const containerRef = ref<HTMLElement | null>(null)
const leftWidthPct = ref(62)
const isDragging   = ref(false)

function onDividerMouseDown(e: MouseEvent) {
  isDragging.value = true
  e.preventDefault()
  const startX    = e.clientX
  const startPct  = leftWidthPct.value
  const container = containerRef.value
  function onMove(ev: MouseEvent) {
    if (!container) return
    const dx     = ev.clientX - startX
    const totalW = container.getBoundingClientRect().width
    leftWidthPct.value = Math.max(35, Math.min(75, startPct + (dx / totalW) * 100))
  }
  function onUp() {
    isDragging.value = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// ─── Left panel tabs ──────────────────────────────────────────────────────────
type LeftTab = 'worker' | 'plan'
const leftTab = ref<LeftTab>('worker')

// ─── All tools — loaded once, grouped on frontend ─────────────────────────────
const allTools = ref<ApiTool[]>([])
const loading  = ref(false)

async function loadAllTools() {
  loading.value = true
  try {
    allTools.value = await toolsStore.fetchAll()
  } finally {
    loading.value = false
  }
}

// Tools grouped by workerId (all assigned tools, including process-level)
const toolsByWorker = computed(() => {
  const map = new Map<string, ApiTool[]>()
  for (const t of allTools.value) {
    if (t.workerId && t.status === 'assigned') {
      if (!map.has(t.workerId)) map.set(t.workerId, [])
      map.get(t.workerId)!.push(t)
    }
  }
  return map
})

// Tools grouped by processId
const toolsByProcess = computed(() => {
  const map = new Map<string, ApiTool[]>()
  for (const t of allTools.value) {
    if (t.processId && t.status === 'assigned') {
      if (!map.has(t.processId)) map.set(t.processId, [])
      map.get(t.processId)!.push(t)
    }
  }
  return map
})

// ─── Worker search ────────────────────────────────────────────────────────────
const workerSearch = ref('')
const filteredWorkers = computed(() => {
  const q = workerSearch.value.toLowerCase().trim()
  if (!q) return workersStore.workers
  return workersStore.workers.filter(w =>
    w.name.toLowerCase().includes(q) || w.workerId.toLowerCase().includes(q),
  )
})

// ─── Register tool ────────────────────────────────────────────────────────────
const showRegister    = ref(false)
const registerForm    = ref({ toolId: '', typeId: '', notes: '' })
const registerLoading = ref(false)

async function doRegister() {
  if (!registerForm.value.toolId.trim()) { toast('Tool ID is required', 'error'); return }
  if (!registerForm.value.typeId)        { toast('Tool type is required', 'error'); return }
  registerLoading.value = true
  try {
    await toolsStore.createTool({
      toolId: registerForm.value.toolId.trim(),
      typeId: registerForm.value.typeId,
      notes:  registerForm.value.notes.trim() || undefined,
    })
    toast(`Tool "${registerForm.value.toolId}" registered!`)
    showRegister.value = false
    registerForm.value = { toolId: '', typeId: '', notes: '' }
    await refresh()
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    registerLoading.value = false
  }
}

// ─── By Control Plan: line / station selectors ───────────────────────────────
const selectedLineId    = ref<string>('')
const selectedStationId = ref<string>('')

const lineStations = computed(() =>
  selectedLineId.value ? (stStore.stations[selectedLineId.value] ?? []) : [],
)

const stationProcesses = computed(() => {
  const stn = lineStations.value.find(s => s.id === selectedStationId.value)
  return stn?.processes.filter(p => p.status === 'active') ?? []
})

watch(selectedLineId, async (id) => {
  selectedStationId.value = ''
  if (id && !stStore.loadedLines.has(id)) {
    await stStore.fetchStations(id)
  }
  selectedStationId.value = lineStations.value[0]?.id ?? ''
})

// ─── Process grouping (same as Worker Assignment view) ───────────────────────
interface ProcessGroup {
  key: string
  displayName: string
  code: string
  extractedCode: string | null
  workerId: string | null
  workerName: string | null
  processes: Process[]
}

const groupedStationProcesses = computed((): ProcessGroup[] => {
  const map = new Map<string, ProcessGroup>()
  for (const p of stationProcesses.value) {
    const key = p.extractedCode || p.id
    if (!map.has(key)) {
      map.set(key, {
        key,
        displayName: p.name,
        code: p.code,
        extractedCode: p.extractedCode,
        workerId: p.workerId,
        workerName: p.workerName,
        processes: [],
      })
    }
    const group = map.get(key)!
    group.processes.push(p)
    // Pick up worker from any process in the group
    if (!group.workerId && p.workerId) {
      group.workerId = p.workerId
      group.workerName = p.workerName
    }
  }
  return [...map.values()]
})

// Collect tools for a process group:
//  1. Tools directly assigned to any processId in the group
//  2. Tools assigned to the group's worker with no specific processId (worker-level)
function toolsForGroup(group: ProcessGroup): ApiTool[] {
  const seen = new Set<string>()
  const result: ApiTool[] = []
  // Process-level tools
  for (const p of group.processes) {
    for (const t of toolsByProcess.value.get(p.id) ?? []) {
      if (!seen.has(t.id)) { seen.add(t.id); result.push(t) }
    }
  }
  // Worker-level tools (no specific process) — shared across all plans
  if (group.workerId) {
    for (const t of toolsByWorker.value.get(group.workerId) ?? []) {
      if (!t.processId && !seen.has(t.id)) { seen.add(t.id); result.push(t) }
    }
  }
  return result
}

// ─── Right panel filters ──────────────────────────────────────────────────────
const searchInput  = ref('')
const filterTypeId = ref('')
const filterStatus = ref('')

let searchTimeout: ReturnType<typeof setTimeout> | null = null
watch(searchInput, () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => refreshRightPanel(), 350)
})
watch([filterTypeId, filterStatus], () => refreshRightPanel())

function refreshRightPanel() {
  toolsStore.fetchTools({
    search: searchInput.value || undefined,
    typeId: filterTypeId.value || undefined,
    status: filterStatus.value || undefined,
    page: 1,
  })
}

// Right panel: unassigned tools first
const sortedRightTools = computed(() =>
  [...toolsStore.tools].sort((a, b) => {
    const av = a.workerId ? 1 : 0
    const bv = b.workerId ? 1 : 0
    return av - bv || a.toolId.localeCompare(b.toolId)
  }),
)

// ─── Pick Tool modal (from left panel "Assign Tool" buttons) ──────────────────
const showPickTool   = ref(false)
const pickTarget     = ref<{ type: 'worker' | 'process'; id: string; name: string } | null>(null)
const pickSearch     = ref('')
const pickTypeFilter = ref('')
const pickedToolId   = ref<string>('')
const pickLoading    = ref(false)

const availableTools = computed(() =>
  allTools.value.filter(t => t.status === 'available'),
)

const filteredPickTools = computed(() => {
  let tools = availableTools.value
  if (pickTypeFilter.value) tools = tools.filter(t => t.typeId === pickTypeFilter.value)
  const q = pickSearch.value.toLowerCase().trim()
  if (q) tools = tools.filter(t =>
    t.toolId.toLowerCase().includes(q) || t.typeName.toLowerCase().includes(q),
  )
  return tools
})

function openPickTool(type: 'worker' | 'process', id: string, name: string) {
  pickTarget.value     = { type, id, name }
  pickSearch.value     = ''
  pickTypeFilter.value = ''
  pickedToolId.value   = ''
  showPickTool.value   = true
}

async function doPickAssign() {
  if (!pickTarget.value || !pickedToolId.value) {
    toast('Please select a tool', 'error')
    return
  }
  pickLoading.value = true
  try {
    const payload = pickTarget.value.type === 'worker'
      ? { workerId: pickTarget.value.id, processId: null }
      : { workerId: null, processId: pickTarget.value.id }
    await toolsStore.assignTool(pickedToolId.value, payload)
    toast('Tool assigned!')
    showPickTool.value = false
    await refresh()
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    pickLoading.value = false
  }
}

// ─── Assign modal (from right panel tool cards) ───────────────────────────────
const showAssign    = ref(false)
const assignToolRef = ref<ApiTool | null>(null)
const assignTarget  = ref<{ workerId: string; processId: string }>({ workerId: '', processId: '' })
const assignLoading = ref(false)

// Worker search inside assign modal
const assignWorkerSearch = ref('')
const filteredAssignWorkers = computed(() => {
  const q = assignWorkerSearch.value.toLowerCase().trim()
  if (!q) return workersStore.workers
  return workersStore.workers.filter(w =>
    w.name.toLowerCase().includes(q) || w.workerId.toLowerCase().includes(q),
  )
})

// All active processes across all loaded stations (for the assign modal dropdown)
const allActiveProcesses = computed(() =>
  stStore.allProcesses.filter(p => p.status === 'active'),
)

function openAssignModal(t: ApiTool) {
  assignToolRef.value = t
  assignTarget.value  = {
    workerId:  t.workerId  || '',
    processId: t.processId || '',
  }
  assignWorkerSearch.value = ''
  showAssign.value = true
}

async function doAssign() {
  if (!assignToolRef.value) return
  assignLoading.value = true
  try {
    await toolsStore.assignTool(assignToolRef.value.id, {
      workerId:  assignTarget.value.workerId  || null,
      processId: assignTarget.value.processId || null,
    })
    toast(assignTarget.value.workerId ? 'Tool assigned!' : 'Tool unassigned', assignTarget.value.workerId ? 'success' : 'warning')
    showAssign.value = false
    await refresh()
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    assignLoading.value = false
  }
}

async function unassignTool(t: ApiTool) {
  try {
    await toolsStore.assignTool(t.id, { workerId: null, processId: null })
    toast('Tool unassigned', 'warning')
    await refresh()
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function refresh() {
  await Promise.all([
    loadAllTools(),
    toolsStore.fetchTools({
      search: searchInput.value || undefined,
      typeId: filterTypeId.value || undefined,
      status: filterStatus.value || undefined,
      page: 1,
    }),
  ])
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusColor(s: string) {
  return {
    available: 'bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 dark:border dark:border-green-500/30',
    assigned:  'bg-brand-500 text-white dark:bg-brand-500/15 dark:text-brand-400 dark:border dark:border-brand-500/30',
    faulty:    'bg-red-600 text-white dark:bg-red-500/15 dark:text-red-400 dark:border dark:border-red-500/30',
    in_repair: 'bg-amber-500 text-white dark:bg-amber-500/15 dark:text-amber-400 dark:border dark:border-amber-500/30',
  }[s] ?? 'bg-surface-700 text-surface-300'
}

function statusLabel(s: string) {
  return { available: 'Available', assigned: 'Assigned', faulty: 'Faulty', in_repair: 'In Repair' }[s] ?? s
}

function statusDot(s: string) {
  return { available: 'bg-green-400', assigned: 'bg-brand-400', faulty: 'bg-red-400', in_repair: 'bg-amber-400' }[s] ?? 'bg-surface-400'
}

// Group a tool list by type with limit info
function groupByType(tools: ApiTool[]) {
  const map = new Map<string, { typeName: string; typeId: string; maxPerWorker: number; tools: ApiTool[] }>()
  for (const t of tools) {
    if (!map.has(t.typeId)) {
      const tt = toolTypesStore.types.find(x => x.id === t.typeId)
      map.set(t.typeId, { typeName: t.typeName, typeId: t.typeId, maxPerWorker: tt?.maxPerWorker ?? 1, tools: [] })
    }
    map.get(t.typeId)!.tools.push(t)
  }
  return [...map.values()]
}

// ─── Init ─────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    workersStore.fetchWorkers(),
    toolTypesStore.fetchTypes(),
    toolsStore.fetchTools(),
    loadAllTools(),
  ])
  if (linesStore.lines.length > 0) {
    selectedLineId.value = linesStore.lines[0].id
  }
})
</script>

<template>
  <div class="p-8 h-full flex flex-col">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <PageHeader
        title="Tool Allocation"
        :subtitle="`${allTools.filter(t => !t.workerId).length} unassigned tool(s)`"/>
      <button @click="refresh"
        class="text-surface-400 hover:text-surface-200 transition-colors p-2 rounded-lg hover:bg-surface-800"
        title="Refresh">
        <RefreshCw :size="15"/>
      </button>
    </div>

    <!-- Two-panel resizable layout -->
    <div ref="containerRef"
      class="flex flex-1 gap-0 min-h-0 overflow-hidden rounded-2xl border border-surface-700"
      :class="isDragging ? 'select-none cursor-col-resize' : ''">

      <!-- ── LEFT PANEL ──────────────────────────────────────────────────────── -->
      <div class="flex flex-col min-w-0 overflow-hidden bg-surface-950"
           :style="{ width: leftWidthPct + '%' }">

        <!-- Tabs -->
        <div class="flex border-b border-surface-700 flex-shrink-0">
          <button @click="leftTab = 'worker'"
            :class="['flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors border-b-2',
                     leftTab === 'worker' ? 'text-brand-400 border-brand-500 bg-brand-500/5' : 'text-surface-400 border-transparent hover:text-surface-200']">
            <HardHat :size="14"/> By Worker
          </button>
          <button @click="leftTab = 'plan'"
            :class="['flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors border-b-2',
                     leftTab === 'plan' ? 'text-brand-400 border-brand-500 bg-brand-500/5' : 'text-surface-400 border-transparent hover:text-surface-200']">
            <ClipboardList :size="14"/> By Control Plan
          </button>
        </div>

        <!-- Loading skeleton -->
        <div v-if="loading" class="flex-1 p-3 space-y-2">
          <AppSkeleton v-for="i in 8" :key="i" height="h-14" rounded="rounded-xl"/>
        </div>

        <!-- ── BY WORKER ─────────────────────────────────────────────────────── -->
        <template v-else-if="leftTab === 'worker'">
          <!-- Worker search -->
          <div class="px-4 py-2.5 border-b border-surface-700 flex-shrink-0">
            <div class="relative">
              <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
              <input v-model="workerSearch" placeholder="Search by name or ID…"
                class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-4 space-y-3">
            <div v-if="filteredWorkers.length === 0" class="text-center py-16 text-surface-400 text-sm">
              No workers found
            </div>
            <div v-for="w in filteredWorkers" :key="w.id"
              class="bg-surface-900 rounded-xl border border-surface-700 overflow-hidden">
              <!-- Worker header -->
              <div class="flex items-center gap-3 px-4 py-3 border-b border-surface-800">
                <div class="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-300 flex-shrink-0">
                  {{ w.name.charAt(0).toUpperCase() }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-bold text-slate-200 truncate">{{ w.name }}</div>
                  <div class="text-[10px] font-mono text-surface-400">{{ w.workerId }}</div>
                </div>
                <AppButton size="sm" @click="openPickTool('worker', w.id, w.name)" class="flex-shrink-0">
                  <Wrench :size="12"/> Assign Tool
                </AppButton>
              </div>

              <!-- Tool groups -->
              <div class="px-4 py-3">
                <div v-if="!toolsByWorker.get(w.id)?.length" class="text-xs text-surface-500 italic">
                  No tools assigned
                </div>
                <div v-else class="space-y-2">
                  <div v-for="group in groupByType(toolsByWorker.get(w.id) ?? [])" :key="group.typeId">
                    <div class="flex items-center gap-1.5 mb-1.5">
                      <Tag :size="10" class="text-surface-500"/>
                      <span class="text-[10px] font-bold text-surface-400 uppercase tracking-wider">{{ group.typeName }}</span>
                      <span :class="['px-1 py-0.5 rounded text-[9px] font-bold',
                                     group.tools.length >= group.maxPerWorker
                                       ? 'bg-red-500/15 text-red-400'
                                       : 'bg-green-500/15 text-green-400']">
                        {{ group.tools.length }}/{{ group.maxPerWorker }}
                      </span>
                    </div>
                    <div class="space-y-1">
                      <div v-for="t in group.tools" :key="t.id"
                        class="flex items-center gap-2 bg-surface-800 rounded-lg px-3 py-2 border border-surface-700">
                        <div :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', statusDot(t.status)]"/>
                        <span class="text-xs font-bold font-mono text-slate-200 flex-1 truncate">{{ t.toolId }}</span>
                        <span v-if="t.processName" class="text-[10px] text-surface-500 truncate max-w-[100px]">· {{ t.processName }}</span>
                        <button @click="unassignTool(t)"
                          class="text-surface-500 hover:text-red-400 transition-colors p-0.5 flex-shrink-0">
                          <X :size="11"/>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ── BY CONTROL PLAN ───────────────────────────────────────────────── -->
        <template v-else>
          <!-- Line + Station selectors -->
          <div class="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-surface-700 flex-shrink-0">
            <div class="relative">
              <select v-model="selectedLineId"
                class="appearance-none bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
                <option v-for="l in linesStore.lines" :key="l.id" :value="l.id">{{ l.name }}</option>
              </select>
              <ChevronDown :size="12" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
            </div>
            <div class="relative">
              <select v-model="selectedStationId" :disabled="lineStations.length === 0"
                class="appearance-none bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer disabled:opacity-50">
                <option v-for="s in lineStations" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <ChevronDown :size="12" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
            </div>
          </div>

          <!-- Grouped control plans -->
          <div class="flex-1 overflow-y-auto p-4 space-y-3">
            <div v-if="!selectedStationId" class="text-center py-16 text-surface-400 text-sm">
              Select a line and station
            </div>
            <div v-else-if="groupedStationProcesses.length === 0" class="text-center py-16 text-surface-400 text-sm">
              No active control plans in this station
            </div>

            <div v-for="group in groupedStationProcesses" :key="group.key"
              class="bg-surface-900 rounded-xl border border-surface-700 overflow-hidden">

              <!-- Group header -->
              <div class="flex items-start gap-3 px-4 py-3 border-b border-surface-800">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-bold text-slate-200">{{ group.displayName }}</span>
                    <!-- Car model badges when grouped -->
                    <template v-if="group.processes.length > 1">
                      <span v-for="p in group.processes" :key="p.id"
                        class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium
                               bg-surface-700 text-surface-300 border border-surface-600">
                        <Car :size="9"/>
                        {{ p.carModel?.name ?? p.name }}
                      </span>
                    </template>
                  </div>
                  <div class="flex items-center gap-2 mt-1 flex-wrap">
                    <span class="text-[10px] font-mono text-surface-500">{{ group.code }}</span>
                    <span v-if="group.workerName"
                      class="inline-flex items-center gap-1 text-[10px] font-medium
                             bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 rounded px-1.5 py-0.5">
                      <User :size="9"/> {{ group.workerName }}
                    </span>
                    <span v-else class="text-[10px] text-amber-500 italic">No worker assigned</span>
                  </div>
                </div>
                <AppButton
                  size="sm"
                  :disabled="!group.workerId"
                  :title="!group.workerId ? 'Assign a worker to this plan first' : `Assign tool to ${group.workerName}`"
                  @click="group.workerId && openPickTool('worker', group.workerId, group.workerName ?? group.displayName)"
                  class="flex-shrink-0 mt-0.5">
                  <Wrench :size="12"/> Assign Tool
                </AppButton>
              </div>

              <!-- Tools for this group -->
              <div class="px-4 py-3">
                <template v-if="toolsForGroup(group).length === 0">
                  <div class="text-xs text-surface-500 italic">No tools assigned</div>
                </template>
                <div v-else class="space-y-1">
                  <div v-for="t in toolsForGroup(group)" :key="t.id"
                    class="flex items-center gap-2 bg-surface-800 rounded-lg px-3 py-2 border border-surface-700">
                    <div :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', statusDot(t.status)]"/>
                    <span class="text-xs font-bold font-mono text-slate-200 flex-1 truncate">{{ t.toolId }}</span>
                    <span class="text-[10px] text-surface-500">{{ t.typeName }}</span>
                    <!-- Show which specific process if assigned to one in group -->
                    <span v-if="t.processId && group.processes.length > 1"
                      class="text-[10px] text-surface-600 truncate max-w-[80px]">
                      · {{ t.processName }}
                    </span>
                    <button @click="unassignTool(t)"
                      class="text-surface-500 hover:text-red-400 transition-colors p-0.5 flex-shrink-0">
                      <X :size="11"/>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- ── DIVIDER ─────────────────────────────────────────────────────────── -->
      <div class="w-1.5 bg-surface-800 hover:bg-brand-500/40 cursor-col-resize flex-shrink-0 transition-colors"
           @mousedown="onDividerMouseDown"/>

      <!-- ── RIGHT PANEL: tool inventory ──────────────────────────────────────── -->
      <div class="flex flex-col min-w-0 overflow-hidden bg-surface-950 flex-1">
        <div class="flex items-center gap-2 px-4 py-3 border-b border-surface-700 flex-shrink-0">
          <span class="text-xs font-bold text-surface-300 uppercase tracking-wider flex-1">Tools</span>
          <span class="text-xs text-surface-500 mr-1">{{ toolsStore.total }} total</span>
          <AppButton size="sm" @click="showRegister = true"><Plus :size="12"/> Register</AppButton>
        </div>

        <!-- Filters -->
        <div class="px-4 pt-3 pb-2 space-y-2 flex-shrink-0">
          <div class="relative">
            <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
            <input v-model="searchInput" placeholder="Search by ID…"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
          </div>
          <div class="flex gap-2">
            <div class="relative flex-1">
              <select v-model="filterTypeId"
                class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-7 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
                <option value="">All types</option>
                <option v-for="tt in toolTypesStore.types" :key="tt.id" :value="tt.id">{{ tt.name }}</option>
              </select>
              <ChevronDown :size="11" class="absolute right-2 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
            </div>
            <div class="relative flex-1">
              <select v-model="filterStatus"
                class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-7 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
                <option value="">All status</option>
                <option value="available">Available</option>
                <option value="assigned">Assigned</option>
                <option value="faulty">Faulty</option>
                <option value="in_repair">In Repair</option>
              </select>
              <ChevronDown :size="11" class="absolute right-2 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
            </div>
          </div>
        </div>

        <!-- Tool cards -->
        <div class="flex-1 overflow-y-auto px-4 pb-4 space-y-1.5">
          <div v-if="sortedRightTools.length === 0" class="text-center py-10 text-surface-400 text-xs">No tools found</div>
          <div v-for="t in sortedRightTools" :key="t.id"
            :class="['flex items-center gap-3 rounded-xl px-3 py-2.5 border transition-all',
                     t.workerId
                       ? 'bg-surface-900 border-surface-700 hover:border-surface-500'
                       : 'bg-surface-900 border-amber-500/20 hover:border-amber-500/40']">
            <div :class="['w-2 h-2 rounded-full flex-shrink-0', statusDot(t.status)]"/>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-bold text-slate-200 font-mono truncate">{{ t.toolId }}</div>
              <div class="text-[10px] text-surface-400 mt-0.5">
                {{ t.typeName }}
                <span v-if="t.workerName"> · {{ t.workerName }}</span>
                <span v-if="t.processName"> · {{ t.processName }}</span>
              </div>
            </div>
            <span :class="['px-1.5 py-0.5 rounded text-[10px] font-bold flex-shrink-0', statusColor(t.status)]">
              {{ statusLabel(t.status) }}
            </span>
            <button @click="openAssignModal(t)"
              :disabled="t.status === 'faulty' || t.status === 'in_repair'"
              :class="['text-surface-500 hover:text-brand-400 transition-colors p-1 rounded hover:bg-surface-700 flex-shrink-0',
                       (t.status === 'faulty' || t.status === 'in_repair') ? 'opacity-30 cursor-not-allowed' : '']"
              title="Assign tool">
              <Wrench :size="11"/>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Register Tool Modal ───────────────────────────────────────────────── -->
    <AppModal :open="showRegister" title="Register Tool" @close="showRegister = false">
      <div class="space-y-4 mb-5">
        <FormField label="Tool ID">
          <AppInput v-model="registerForm.toolId" placeholder="e.g. DRILL-001" @keyup.enter="doRegister"/>
        </FormField>
        <FormField label="Tool Type">
          <div class="relative">
            <select v-model="registerForm.typeId"
              class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
              <option value="" disabled>Select type…</option>
              <option v-for="tt in toolTypesStore.types" :key="tt.id" :value="tt.id">
                {{ tt.name }} (max {{ tt.maxPerWorker }}/worker)
              </option>
            </select>
            <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
        </FormField>
        <FormField label="Notes (optional)">
          <AppInput v-model="registerForm.notes" placeholder="Any notes about this tool…"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showRegister = false">Cancel</AppButton>
        <AppButton :disabled="registerLoading" @click="doRegister">
          {{ registerLoading ? 'Registering…' : 'Register Tool' }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Pick Tool Modal (assign from worker/plan group cards) ────────────── -->
    <AppModal
      :open="showPickTool"
      :title="pickTarget ? `Assign Tool → ${pickTarget.name}` : 'Assign Tool'"
      @close="showPickTool = false">

      <!-- Filters -->
      <div class="space-y-2 mb-4">
        <div class="relative">
          <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
          <input v-model="pickSearch" placeholder="Search by tool ID or type…"
            class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
        </div>
        <div class="relative">
          <select v-model="pickTypeFilter"
            class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
            <option value="">All types</option>
            <option v-for="tt in toolTypesStore.types" :key="tt.id" :value="tt.id">{{ tt.name }}</option>
          </select>
          <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
        </div>
      </div>

      <!-- Available tools list -->
      <div class="max-h-64 overflow-y-auto space-y-1.5 mb-5 pr-1">
        <div v-if="filteredPickTools.length === 0"
          class="text-center py-8 text-surface-400 text-sm">
          No available tools{{ pickSearch || pickTypeFilter ? ' matching your filter' : '' }}
        </div>
        <button v-for="t in filteredPickTools" :key="t.id"
          @click="pickedToolId = t.id"
          :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border text-left transition-all',
                   pickedToolId === t.id
                     ? 'bg-brand-500/10 border-brand-500/50 text-brand-300'
                     : 'bg-surface-800 border-surface-700 hover:border-surface-500 text-slate-200']">
          <div class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors"
               :class="pickedToolId === t.id ? 'border-brand-400 bg-brand-500' : 'border-surface-500'">
            <Check v-if="pickedToolId === t.id" :size="10" class="text-white"/>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-bold font-mono truncate">{{ t.toolId }}</div>
            <div class="text-[10px] text-surface-400 mt-0.5">{{ t.typeName }}</div>
          </div>
          <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 flex-shrink-0">
            Available
          </span>
        </button>
      </div>

      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showPickTool = false">Cancel</AppButton>
        <AppButton :disabled="pickLoading || !pickedToolId" @click="doPickAssign">
          {{ pickLoading ? 'Assigning…' : 'Assign Tool' }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Assign Modal (from right panel tool cards) ──────────────────────── -->
    <AppModal :open="showAssign"
      :title="assignToolRef ? `Assign — ${assignToolRef.toolId}` : 'Assign Tool'"
      @close="showAssign = false">

      <p class="text-xs text-surface-400 mb-4">
        Assign to a worker (direct) or a control plan (inherits the plan's worker). Leave both empty to unassign.
      </p>

      <div class="space-y-4 mb-5">
        <FormField label="Assign to Worker">
          <!-- Worker search -->
          <div class="relative mb-2">
            <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
            <input v-model="assignWorkerSearch" placeholder="Search worker…"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
          </div>
          <div class="relative">
            <select v-model="assignTarget.workerId"
              @change="assignTarget.processId = ''"
              class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
              <option value="">None (unassign)</option>
              <option v-for="w in filteredAssignWorkers" :key="w.id" :value="w.id">
                {{ w.name }} ({{ w.workerId }})
              </option>
            </select>
            <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
        </FormField>

        <div class="flex items-center gap-3">
          <div class="h-px flex-1 bg-surface-700"/>
          <span class="text-xs text-surface-500">OR</span>
          <div class="h-px flex-1 bg-surface-700"/>
        </div>

        <FormField label="Assign to Control Plan">
          <div class="relative">
            <select v-model="assignTarget.processId"
              @change="assignTarget.workerId = ''"
              class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
              <option value="">None</option>
              <option v-for="p in allActiveProcesses" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
        </FormField>
      </div>

      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAssign = false">Cancel</AppButton>
        <AppButton :disabled="assignLoading" @click="doAssign">
          {{ assignLoading ? 'Saving…' : 'Confirm' }}
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
