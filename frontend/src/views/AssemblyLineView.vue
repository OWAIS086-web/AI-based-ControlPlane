<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLinesStore } from '@/stores/lines'
import { useAuthStore } from '@/stores/auth'
import { useStationsStore } from '@/stores/stations'
import { useCarModelsStore } from '@/stores/carModels'
import { useMigrationsStore } from '@/stores/migrations'
import { useConfigStore } from '@/stores/config'
import { useWorkersStore } from '@/stores/workers'
import { useToast } from '@/composables/useToast'
import type { Process } from '@/stores/stations'
import { api } from '@/services/api'
import { processesService } from '@/services/processes.service'
import AppCard    from '@/components/ui/AppCard.vue'
import AppButton  from '@/components/ui/AppButton.vue'
import AppBadge   from '@/components/ui/AppBadge.vue'
import AddStationModal         from '@/components/modals/AddStationModal.vue'
import AddProcessModal         from '@/components/modals/AddProcessModal.vue'
import ImportProcessNamesModal from '@/components/modals/ImportProcessNamesModal.vue'
import MigrateProcessesModal   from '@/components/modals/MigrateProcessesModal.vue'
import ImportProcessesModal    from '@/components/modals/ImportProcessesModal.vue'
import AssignWorkerModal       from '@/components/modals/AssignWorkerModal.vue'
import DeleteStationDialog     from '@/components/ui/DeleteStationDialog.vue'
import DeleteProcessDialog     from '@/components/ui/DeleteProcessDialog.vue'
import ConfirmDialog           from '@/components/ui/ConfirmDialog.vue'
import UploadPanel             from '@/components/upload/UploadPanel.vue'
import AIStatusBadge           from '@/components/ui/AIStatusBadge.vue'
import SkeletonCards            from '@/components/ui/SkeletonCards.vue'
import AppSkeleton              from '@/components/ui/AppSkeleton.vue'
import { useAIStatusStore } from '@/stores/aiStatus'
import type { Component } from 'vue'
import {
  Plus, Trash2, ArrowRightLeft, Archive, RotateCcw, Pencil,
  Scissors, Wrench, Settings, Building2, Flag, Construction, Car, Copy, Download, UploadCloud,
  User, UserCheck,
} from 'lucide-vue-next'

// Icon map keyed by icon-name string (lowercase, matches DB values)
const LINE_ICONS: Record<string, Component> = {
  scissors: Scissors, wrench: Wrench, settings: Settings, building2: Building2,
  flag: Flag, car: Car, zap: Construction, box: Construction, factory: Construction,
}

const route  = useRoute()
const router = useRouter()
const auth          = useAuthStore()
const stStore       = useStationsStore()
const aiStatusStore = useAIStatusStore()

// SSE store takes priority for real-time updates; fall back to process's own field
function getAIStatus(p: { id: string; aiStatus: 'idle' | 'ai_running' | 'completed' | 'failed' }) {
  return aiStatusStore.statuses[p.id] ?? p.aiStatus
}
const cmStore     = useCarModelsStore()
const migStore    = useMigrationsStore()
const configStore = useConfigStore()
const { toast }   = useToast()

const linesStore    = useLinesStore()
const workersStore  = useWorkersStore()
const lineId        = computed(() => route.params.lineId as string)
const line          = computed(() => linesStore.lines.find(l => l.id === lineId.value))
const lineStations  = computed(() => stStore.stations[lineId.value] ?? [])
const activeStation = ref<string | null>(null)
const activeModel   = ref<string | null>(null)
const showArchived  = ref(false)
const loading       = ref(false)

// ─── Multi-select ─────────────────────────────────────────────────────────────
const selectedIds       = ref<Set<string>>(new Set())
const bulkDeleteConfirm = ref(false)

watch([activeStation, activeModel, showArchived], () => { selectedIds.value = new Set() })

const allSelected = computed(() =>
  visibleProcs.value.length > 0 && visibleProcs.value.every(p => selectedIds.value.has(p.id))
)

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(visibleProcs.value.map(p => p.id))
  }
}

async function bulkArchive() {
  const ids = [...selectedIds.value]
  try {
    await stStore.bulkSetProcessStatus(lineId.value, activeStation.value!, ids, 'archived')
    toast(`${ids.length} process(es) archived`, 'warning')
    selectedIds.value = new Set()
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function bulkDelete() {
  const ids = [...selectedIds.value]
  try {
    await stStore.bulkDeleteProcesses(lineId.value, activeStation.value!, ids)
    toast(`${ids.length} process(es) deleted`, 'warning')
    selectedIds.value = new Set()
    bulkDeleteConfirm.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

const curStn                = computed(() => lineStations.value.find(s => s.id === activeStation.value))
const hasActiveCarModels    = computed(() => cmStore.activeCarModels.length > 0)
const curStnTotalProcsCount = computed(() => curStn.value?.processes.length ?? 0)

const visibleProcs = computed(() =>
  (curStn.value?.processes ?? []).filter(p =>
    p.status === (!auth.isLM && showArchived.value ? 'archived' : 'active') &&
    p.carModelId === activeModel.value,
  ),
)

// ─── Query param sync ─────────────────────────────────────────────────────────
watch([activeStation, activeModel, showArchived], ([stn, car, arch]) => {
  router.replace({
    query: {
      ...route.query,
      station:  stn  ?? undefined,
      car:      car  ?? undefined,
      archived: arch ? 'true' : undefined,
    },
  })
})

// ─── Helpers ──────────────────────────────────────────────────────────────────
function resolveStation(candidate: string | null): string | null {
  if (candidate && lineStations.value.some(s => s.id === candidate)) return candidate
  return lineStations.value[0]?.id ?? null
}
function resolveCarModel(candidate: string | null): string | null {
  if (candidate && cmStore.activeCarModels.some(m => m.id === candidate)) return candidate
  return cmStore.activeCarModels[0]?.id ?? null
}

// ─── Data loading ─────────────────────────────────────────────────────────────
onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([stStore.fetchStations(lineId.value), cmStore.fetchCarModels(), configStore.fetchConfig()])
    activeStation.value = resolveStation((route.query.station as string) ?? null)
    activeModel.value   = resolveCarModel((route.query.car as string) ?? null)
    showArchived.value  = route.query.archived === 'true'
    // Seed AI statuses from loaded processes and open SSE stream
    const allProcs = Object.values(stStore.stations[lineId.value] ?? []).flatMap(s => s.processes)
    aiStatusStore.seedFromProcesses(allProcs)
    aiStatusStore.connect()
  } finally {
    loading.value = false
  }
})

watch(lineId, async (newId, oldId) => {
  if (newId === oldId) return
  loading.value = true
  try {
    await stStore.fetchStations(newId)
    activeStation.value = resolveStation(activeStation.value)
  } finally {
    loading.value = false
  }
})

// ─── Upload panel ─────────────────────────────────────────────────────────────
const uploadPanelOpen = ref(false)

// ─── Modal flags ──────────────────────────────────────────────────────────────
const addStnOpen       = ref(false)
const delStnOpen       = ref(false)
const addProcOpen      = ref(false)
const importOpen       = ref(false)
const importProcOpen   = ref(false)
const migrOpen         = ref(false)
const delProcOpen      = ref(false)
const delProcTarget    = ref<{ id: string; name: string } | null>(null)
const importLoading    = ref(false)
const importProcLoading = ref(false)

// ─── Handlers ─────────────────────────────────────────────────────────────────
async function onAddStation(name: string) {
  if (!name.trim()) { toast('Name required', 'error'); return }
  try {
    const id = await stStore.addStation(lineId.value, name)
    // Refresh lines so stationCount updates (drives the v-else-if template branch)
    await linesStore.fetchLines()
    activeStation.value = id
    addStnOpen.value    = false
    toast('Station added!')
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function onDeleteStation() {
  try {
    await stStore.deleteStation(lineId.value, activeStation.value!)
    activeStation.value = lineStations.value[0]?.id ?? null
    toast('Station deleted', 'warning')
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

const renameStnOpen = ref(false)
const renameStnVal  = ref('')

function openRenameStation() {
  renameStnVal.value = curStn.value?.name ?? ''
  renameStnOpen.value = true
}

async function onRenameStation() {
  if (!renameStnVal.value.trim()) { toast('Name required', 'error'); return }
  try {
    await stStore.renameStation(lineId.value, activeStation.value!, renameStnVal.value.trim())
    renameStnOpen.value = false
    toast('Station renamed!')
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function onAddProcess(name: string) {
  if (!name.trim()) { toast('Name required', 'error'); return }
  try {
    await stStore.addProcess(lineId.value, activeStation.value!, name, activeModel.value!)
    toast(`Process "${name}" added!`)
    addProcOpen.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function onImport(names: string[], carModelId: string) {
  importLoading.value = true
  try {
    const created = await api.post<unknown[]>(
      `/lines/${lineId.value}/stations/${activeStation.value}/processes/bulk`,
      { names, carModelId },
    )
    toast(
      created.length
        ? `Imported ${created.length} process(es) successfully!`
        : 'All selected processes already exist for this car model.',
      created.length ? 'success' : 'warning',
    )
    importOpen.value = false
    await stStore.fetchStations(lineId.value)
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    importLoading.value = false
  }
}

async function onImportProcesses(processIds: string[]) {
  if (!processIds.length) return
  importProcLoading.value = true
  try {
    const created = await processesService.importProcesses(
      lineId.value,
      activeStation.value!,
      { processIds, carModelId: activeModel.value!, mode: 'copy' },
    )
    toast(
      created.length
        ? `Imported ${created.length} process(es) successfully!`
        : 'All selected processes already exist for this car model.',
      created.length ? 'success' : 'warning',
    )
    importProcOpen.value = false
    await stStore.fetchStations(lineId.value)
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    importProcLoading.value = false
  }
}

async function onMigrate(fromLine: string, fromStation: string, processIds: string[]) {
  if (!fromStation || !processIds.length) { toast('Select station and at least one process', 'error'); return }
  try {
    await migStore.migrateProcesses(fromLine, fromStation, lineId.value, activeStation.value!, processIds)
    toast(`Migrated ${processIds.length} process(es) successfully!`)
    migrOpen.value = false
    // Refresh both source and target lines so moves are reflected immediately
    const fetches = [stStore.fetchStations(lineId.value)]
    if (fromLine !== lineId.value) fetches.push(stStore.fetchStations(fromLine))
    await Promise.all(fetches)
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

function openDeleteProcess(id: string, name: string) {
  delProcTarget.value = { id, name }
  delProcOpen.value   = true
}

async function onDeleteProcess() {
  if (!delProcTarget.value) return
  try {
    await stStore.deleteProcess(lineId.value, activeStation.value!, delProcTarget.value.id)
    toast(`Process "${delProcTarget.value.name}" deleted`, 'warning')
    delProcTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function toggleStatus(processId: string, status: 'active' | 'archived') {
  try {
    await stStore.setProcessStatus(lineId.value, activeStation.value!, processId, status)
    toast(
      status === 'archived' ? 'Process archived' : 'Process restored!',
      status === 'archived' ? 'warning' : 'success',
    )
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

function viewProcess(processId: string) {
  router.push({
    name: 'process-detail',
    params: { lineId: lineId.value, processId },
    query: { car: activeModelName.value || undefined },
  })
}

// ─── Worker assignment ────────────────────────────────────────────────────────
const assignWorkerOpen   = ref(false)
const assignWorkerTarget = ref<Process | null>(null)

function openAssignWorker(p: Process) {
  assignWorkerTarget.value = p
  assignWorkerOpen.value   = true
}

async function onWorkerAssigned(workerId: string | null) {
  if (!assignWorkerTarget.value) return
  try {
    const target = assignWorkerTarget.value
    // Assign all active processes in the same station that share the extractedCode
    const processIds = target.extractedCode
      ? (curStn.value?.processes ?? [])
          .filter(p => p.extractedCode === target.extractedCode && p.status === 'active')
          .map(p => p.id)
      : [target.id]

    await workersStore.assignWorker(processIds, workerId)
    toast(workerId ? 'Worker assigned!' : 'Assignment removed', workerId ? 'success' : 'warning')
    assignWorkerOpen.value   = false
    assignWorkerTarget.value = null
    await stStore.fetchStations(lineId.value)
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

const unassignedInView = computed(() =>
  visibleProcs.value.filter(p => !p.workerId).length,
)

// ─── Card display label ───────────────────────────────────────────────────────
function cardLabel(p: Process) {
  if (configStore.cardDisplayMode === 'filename') {
    return p.latestVersion?.fileName ?? p.name
  }
  return p.name
}

// ─── Import modal derived props ───────────────────────────────────────────────
const importSourceOptions = computed(() =>
  cmStore.activeCarModels
    .filter(m => m.id !== activeModel.value)
    .map(m => ({ value: m.id, label: m.name })),
)
const activeModelName = computed(
  () => cmStore.activeCarModels.find(m => m.id === activeModel.value)?.name ?? '',
)
</script>

<template>
  <div class="p-8">
    <!-- Line header -->
    <div class="flex items-center gap-4 mb-7">
      <div class="w-12 h-12 rounded-xl flex items-center justify-center" :style="{ background: line?.color + '22' }">
        <component :is="LINE_ICONS[line?.icon ?? ''] ?? Construction" :size="22" :style="{ color: line?.color }" />
      </div>
      <div>
        <h1 class="text-2xl font-black text-slate-100">{{ line?.name }}</h1>
        <p class="text-sm text-surface-200">Process Control Management</p>
      </div>
    </div>

    <!-- Loading skeleton -->
    <template v-if="loading">
      <!-- Station tab skeletons -->
      <div class="flex gap-2 mb-5">
        <AppSkeleton v-for="i in 4" :key="i" height="h-8" width="w-24" rounded="rounded-lg"/>
      </div>
      <!-- Process card skeletons -->
      <SkeletonCards :count="8"/>
    </template>

    <!-- Coming soon -->
    <template v-else-if="line?.stationCount === 0">
      <AppCard class="text-center py-16">
        <Construction :size="48" class="mx-auto mb-4 text-surface-400"/>
        <h3 class="text-lg font-bold text-slate-100 mb-2">{{ line?.name }} Coming Soon</h3>
        <p class="text-sm text-surface-200 mb-5">Not yet operational.</p>
        <AppButton v-if="auth.isPM" @click="addStnOpen = true"><Plus :size="15"/> Add First Station</AppButton>
      </AppCard>
    </template>

    <!-- No stations -->
    <template v-else-if="lineStations.length === 0">
      <AppCard class="text-center py-16">
        <Construction :size="48" class="mx-auto mb-4 text-surface-400"/>
        <h3 class="text-lg font-bold text-slate-100 mb-2">No Stations Yet</h3>
        <p class="text-sm text-surface-200 mb-5">This line has no stations configured.</p>
        <AppButton v-if="auth.isPM" @click="addStnOpen = true"><Plus :size="15"/> Add First Station</AppButton>
      </AppCard>
    </template>

    <template v-else>
      <!-- Station tabs -->
      <div class="flex items-center gap-2 mb-5 flex-wrap">
        <div class="flex gap-1.5 flex-1 flex-wrap">
          <button v-for="s in lineStations" :key="s.id"
            @click="activeStation = s.id; showArchived = false"
            :class="['px-3 py-1.5 rounded-lg text-xs font-bold transition-all',
                     activeStation === s.id ? 'text-white' : 'bg-surface-800 text-surface-200 hover:bg-surface-700']"
            :style="activeStation === s.id ? { background: line?.color } : {}">
            {{ s.name }}
          </button>
        </div>
        <div v-if="auth.isPM" class="flex gap-2">
          <AppButton size="sm" @click="addStnOpen = true"><Plus :size="14"/> Station</AppButton>
          <AppButton size="sm" variant="secondary" v-if="curStn" @click="openRenameStation" title="Rename station"><Pencil :size="14"/></AppButton>
          <AppButton size="sm" variant="danger" v-if="curStn" @click="delStnOpen = true"><Trash2 :size="14"/></AppButton>
          <AppButton size="sm" variant="secondary" @click="migrOpen = true"><ArrowRightLeft :size="14"/> Migrate</AppButton>
        </div>
      </div>

      <template v-if="curStn">
        <!-- Station meta bar -->
        <AppCard class="mb-4 !py-3 !px-4 flex items-center gap-6 flex-wrap">
          <span class="text-xs text-surface-200">Active: <strong class="text-slate-200">{{ curStn.processes.filter(p=>p.status==='active'&&p.carModelId===activeModel).length }}</strong></span>
          <span class="text-xs text-surface-200">Total: <strong class="text-slate-200">{{ curStn.processes.filter(p=>p.carModelId===activeModel).length }}</strong></span>
          <span class="text-xs text-red-400">Missing CPs: <strong>{{ curStn.processes.filter(p=>p.hasMissingCP&&p.status==='active'&&p.carModelId===activeModel).length }}</strong></span>
          <span v-if="!auth.isLM" class="text-xs text-amber-400">Archived: <strong>{{ curStn.processes.filter(p=>p.status==='archived'&&p.carModelId===activeModel).length }}</strong></span>
          <span v-if="!showArchived" class="text-xs text-violet-400">Unassigned: <strong>{{ unassignedInView }}</strong></span>
          <button v-if="!auth.isLM" @click="showArchived = !showArchived"
            :class="['ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border',
                     showArchived ? 'bg-amber-500/15 text-amber-400 border-amber-900' : 'bg-surface-700 text-surface-200 border-surface-600']">
            <Archive :size="12"/>
            {{ showArchived ? 'Viewing Archived' : 'View Archived' }}
            <span v-if="curStn.processes.filter(p=>p.status==='archived'&&p.carModelId===activeModel).length"
                  :class="['rounded-full px-1.5 text-[10px]', showArchived ? 'bg-amber-500 text-black' : 'bg-surface-500 text-slate-300']">
              {{ curStn.processes.filter(p=>p.status==='archived'&&p.carModelId===activeModel).length }}
            </span>
          </button>
        </AppCard>

        <!-- No active car models -->
        <template v-if="!hasActiveCarModels">
          <AppCard class="text-center py-12">
            <Car :size="36" class="mx-auto mb-3 text-surface-400"/>
            <h3 class="text-base font-bold text-slate-300 mb-1">No Active Car Models</h3>
            <p class="text-sm text-surface-300">Add an active car model before managing processes.</p>
          </AppCard>
        </template>

        <template v-else>
          <!-- Car model tabs -->
          <div class="flex gap-2 mb-4 items-center flex-wrap">
            <button v-for="m in cmStore.activeCarModels" :key="m.id" @click="activeModel = m.id"
              :class="['px-4 py-1.5 rounded-full text-xs font-bold transition-all border',
                       activeModel === m.id ? '' : 'border-surface-600 text-surface-200 hover:border-surface-500']"
              :style="activeModel === m.id ? { background: m.color+'22', color: m.color, borderColor: m.color } : {}">
              {{ m.name }}
            </button>
            <div v-if="auth.isPM && !showArchived" class="ml-auto flex gap-2">
              <AppButton v-if="importSourceOptions.length > 0" size="sm" variant="secondary" @click="importOpen = true">
                <Copy :size="14"/> Import Names
              </AppButton>
              <AppButton size="sm" variant="secondary" @click="importProcOpen = true">
                <Download :size="14"/> Import Processes
              </AppButton>
              <AppButton size="sm" variant="secondary" @click="uploadPanelOpen = true">
                <UploadCloud :size="14"/> Upload Files
              </AppButton>
              <AppButton size="sm" @click="addProcOpen = true">
                <Plus :size="14"/> Process
              </AppButton>
            </div>
          </div>

          <div v-if="showArchived" class="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/25 rounded-xl mb-4 text-xs text-amber-300">
            <Archive :size="14"/> Showing archived processes.
          </div>

          <!-- Bulk action bar -->
          <div v-if="auth.isPM && visibleProcs.length" class="flex items-center gap-3 mb-3">
            <label class="flex items-center gap-2 cursor-pointer select-none text-xs text-surface-200">
              <input type="checkbox" :checked="allSelected" @change="toggleSelectAll"
                class="w-3.5 h-3.5 rounded accent-brand-500 cursor-pointer"/>
              <span>{{ allSelected ? 'Deselect All' : 'Select All' }}</span>
            </label>
            <template v-if="selectedIds.size > 0">
              <span class="text-xs text-surface-300">{{ selectedIds.size }} selected</span>
              <AppButton v-if="!showArchived" size="sm" variant="danger" @click="bulkArchive">
                <Archive :size="13"/> Archive Selected
              </AppButton>
              <AppButton v-if="showArchived" size="sm" variant="danger" @click="bulkDeleteConfirm = true">
                <Trash2 :size="13"/> Delete Selected
              </AppButton>
              <button class="text-xs text-surface-400 hover:text-surface-200 transition-colors" @click="selectedIds = new Set()">Clear</button>
            </template>
          </div>

          <!-- Process grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            <div v-for="p in visibleProcs" :key="p.id"
                 :class="['bg-surface-900 rounded-xl p-4 border transition-all',
                          selectedIds.has(p.id) ? 'border-brand-500/60 ring-1 ring-brand-500/30' :
                          showArchived ? 'border-amber-500/20 opacity-85' : p.hasMissingCP ? 'border-red-900' : 'border-surface-600']">
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-start gap-2 min-w-0">
                  <input v-if="auth.isPM" type="checkbox" :checked="selectedIds.has(p.id)" @change="toggleSelect(p.id)"
                    class="mt-0.5 w-3.5 h-3.5 flex-shrink-0 rounded accent-brand-500 cursor-pointer"/>
                  <div class="min-w-0">
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <div :class="['text-sm font-bold', showArchived ? 'text-slate-400' : 'text-slate-100']">{{ cardLabel(p) }}</div>
                      <AIStatusBadge :status="getAIStatus(p)" :show-label="false"/>
                    </div>
                    <div class="text-[10px] font-mono text-surface-300 mt-0.5">{{ p.code }}</div>
                  </div>
                </div>
                <AppBadge v-if="showArchived" color="#F59E0B">Archived</AppBadge>
                <AppBadge v-else-if="p.hasMissingCP" color="#EF4444">No CP</AppBadge>
              </div>
              <div class="text-xs text-surface-300 mb-2">
                <template v-if="p.latestVersion">
                  Latest: <span class="font-mono" :style="showArchived ? { color:'#94A3B8' } : { color: line?.color }">{{ p.latestVersion.version }}</span>
                  · {{ p.versionCount }}v
                </template>
                <span v-else class="text-red-400">No control plan</span>
              </div>
              <!-- Worker chip -->
              <div class="mb-3">
                <button v-if="p.workerName" @click.stop="openAssignWorker(p)"
                  class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors
                         bg-green-600 text-white hover:bg-green-700
                         dark:bg-green-500/20 dark:border dark:border-green-500/50 dark:text-green-300 dark:hover:bg-green-500/30">
                  <UserCheck :size="10"/>
                  {{ p.workerName }}
                </button>
                <button v-else @click.stop="openAssignWorker(p)"
                  class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors
                         bg-amber-500 text-white hover:bg-amber-600
                         dark:bg-amber-500/15 dark:border dark:border-amber-500/40 dark:text-amber-300 dark:hover:bg-amber-500/25">
                  <User :size="10"/>
                  Assign worker
                </button>
              </div>
              <div class="flex gap-2">
                <AppButton size="sm" class="flex-1 justify-center"
                  :style="showArchived ? {} : { background: line?.color, color:'#fff', border:'none' }"
                  :variant="showArchived ? 'secondary' : 'primary'"
                  @click="viewProcess(p.id)">View</AppButton>
                <AppButton v-if="auth.isPM" size="sm"
                  :variant="showArchived ? 'success' : 'danger'"
                  @click="toggleStatus(p.id, showArchived ? 'active' : 'archived')">
                  <RotateCcw v-if="showArchived" :size="13"/>
                  <Archive v-else :size="13"/>
                  {{ showArchived ? 'Restore' : 'Archive' }}
                </AppButton>
                <AppButton v-if="auth.isPM && showArchived" size="sm" variant="danger"
                  @click="openDeleteProcess(p.id, p.name)">
                  <Trash2 :size="13"/>
                </AppButton>
              </div>
            </div>
            <div v-if="!visibleProcs.length" class="col-span-full text-center py-12 text-surface-300 text-sm">
              {{ showArchived ? 'No archived processes for this car model.' : 'No active processes for this car model.' }}
            </div>
          </div>
        </template>
      </template>
    </template>

    <!-- ── Modals ──────────────────────────────────────────────────────────── -->
    <AddStationModal
      v-if="addStnOpen"
      @close="addStnOpen = false"
      @confirm="onAddStation"
    />

    <!-- Rename station modal -->
    <Teleport to="body">
      <div v-if="renameStnOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="renameStnOpen = false">
        <div class="bg-surface-900 border border-surface-600 rounded-2xl p-6 w-80 shadow-2xl">
          <h3 class="text-sm font-bold text-slate-100 mb-4">Rename Station</h3>
          <input
            v-model="renameStnVal"
            class="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500 mb-5"
            placeholder="Station name"
            @keyup.enter="onRenameStation"
          />
          <div class="flex gap-2 justify-end">
            <button @click="renameStnOpen = false"
              class="px-4 py-2 rounded-lg text-sm font-medium text-surface-200 hover:bg-surface-700 transition-colors">
              Cancel
            </button>
            <button @click="onRenameStation"
              class="px-4 py-2 rounded-lg text-sm font-bold bg-brand-500 text-white hover:bg-brand-400 transition-colors">
              Rename
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <DeleteStationDialog
      :open="delStnOpen"
      :station-name="curStn?.name"
      :total-procs-count="curStnTotalProcsCount"
      @close="delStnOpen = false"
      @confirm="onDeleteStation"
    />
    <AddProcessModal
      v-if="addProcOpen"
      @close="addProcOpen = false"
      @confirm="onAddProcess"
    />
    <ImportProcessNamesModal
      v-if="importOpen"
      :station-name="curStn?.name ?? ''"
      :target-model-name="activeModelName"
      :target-model-id="activeModel ?? ''"
      :station-processes="curStn?.processes ?? []"
      :source-options="importSourceOptions"
      :loading="importLoading"
      @close="importOpen = false"
      @confirm="onImport"
    />
    <MigrateProcessesModal
      v-if="migrOpen"
      :target-station-name="curStn?.name ?? ''"
      :target-station-id="curStn?.id ?? ''"
      @close="migrOpen = false"
      @confirm="onMigrate"
    />
    <ImportProcessesModal
      v-if="importProcOpen"
      :target-station-name="curStn?.name ?? ''"
      :target-model-name="activeModelName"
      :target-model-id="activeModel ?? ''"
      :target-processes="curStn?.processes ?? []"
      :loading="importProcLoading"
      @close="importProcOpen = false"
      @confirm="onImportProcesses"
    />
    <DeleteProcessDialog
      :open="delProcOpen"
      :process-name="delProcTarget?.name"
      @close="delProcOpen = false"
      @confirm="onDeleteProcess"
    />

    <AssignWorkerModal
      v-if="assignWorkerOpen"
      :open="assignWorkerOpen"
      :process-ids="assignWorkerTarget ? [assignWorkerTarget.id] : []"
      :current-worker-id="assignWorkerTarget?.workerId ?? null"
      :title="`Assign Worker — ${assignWorkerTarget?.name ?? ''}`"
      @close="assignWorkerOpen = false; assignWorkerTarget = null"
      @assigned="onWorkerAssigned"
    />

    <ConfirmDialog
      :open="bulkDeleteConfirm"
      title="Delete Selected Processes"
      danger
      label="Delete"
      :message="`Permanently delete ${selectedIds.size} archived process(es)? This cannot be undone.`"
      @close="bulkDeleteConfirm = false"
      @confirm="bulkDelete"
    />

    <!-- ── Upload panel (always mounted so drag listeners stay active) ─── -->
    <UploadPanel
      :open="uploadPanelOpen"
      :line-id="lineId"
      :station-id="activeStation ?? ''"
      :car-model-id="activeModel ?? ''"
      @close="uploadPanelOpen = false"
    />
  </div>
</template>