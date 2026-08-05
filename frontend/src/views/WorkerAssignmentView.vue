<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLinesStore }    from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useWorkersStore }  from '@/stores/workers'
import { useCarModelsStore } from '@/stores/carModels'
import { useToast }         from '@/composables/useToast'
import type { Worker }      from '@/stores/workers'
import AppCard    from '@/components/ui/AppCard.vue'
import AppButton  from '@/components/ui/AppButton.vue'
import AppModal   from '@/components/ui/AppModal.vue'
import AppInput   from '@/components/ui/AppInput.vue'
import FormField  from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PageHeader   from '@/components/ui/PageHeader.vue'
import SkeletonCards from '@/components/ui/SkeletonCards.vue'
import {
  ChevronDown, User, UserCheck, UserX, Pencil, Trash2,
  Plus, Search, AlertCircle,
} from 'lucide-vue-next'

const linesStore   = useLinesStore()
const stStore      = useStationsStore()
const workersStore = useWorkersStore()
const cmStore      = useCarModelsStore()
const { toast }    = useToast()

// ─── Resizable panel ──────────────────────────────────────────────────────────
const containerRef  = ref<HTMLElement | null>(null)
const leftWidthPct  = ref(66)   // default ~2:1
const isDragging    = ref(false)

function onDividerMouseDown(e: MouseEvent) {
  isDragging.value = true
  e.preventDefault()
  const startX    = e.clientX
  const startPct  = leftWidthPct.value
  const container = containerRef.value

  function onMove(ev: MouseEvent) {
    if (!container) return
    const dx    = ev.clientX - startX
    const totalW = container.getBoundingClientRect().width
    const newPct = startPct + (dx / totalW) * 100
    leftWidthPct.value = Math.max(30, Math.min(80, newPct))
  }
  function onUp() {
    isDragging.value = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// ─── Left panel: line / station selectors ────────────────────────────────────
const selectedLineId    = ref<string | null>(null)
const selectedStationId = ref<string | null>(null)

const lineStations = computed(() =>
  selectedLineId.value ? (stStore.stations[selectedLineId.value] ?? []) : [],
)

watch(selectedLineId, async (id) => {
  selectedStationId.value = null
  if (id && !stStore.loadedLines.has(id)) {
    await stStore.fetchStations(id)
  }
  selectedStationId.value = lineStations.value[0]?.id ?? null
})

const loading = ref(true)
onMounted(async () => {
  try {
    await Promise.all([cmStore.fetchCarModels(), workersStore.fetchWorkers()])
    if (linesStore.lines.length > 0) selectedLineId.value = linesStore.lines[0]?.id ?? null
  } finally { loading.value = false }
})

// ─── Grouped control plans (by extractedCode) ─────────────────────────────────

interface ControlPlanGroup {
  extractedCode: string | null
  displayName: string
  processIds: string[]
  carModels: { id: string; name: string; color: string }[]
  workerId: string | null
  workerName: string | null
}

const currentStation = computed(() =>
  lineStations.value.find(s => s.id === selectedStationId.value),
)

const controlPlanGroups = computed((): ControlPlanGroup[] => {
  const stn = currentStation.value
  if (!stn) return []

  const activeProcs = stn.processes.filter(p => p.status === 'active')
  const grouped = new Map<string, ControlPlanGroup>()

  for (const p of activeProcs) {
    const key = p.extractedCode ?? p.id  // fallback: each process is its own group
    if (!grouped.has(key)) {
      const cm = cmStore.activeCarModels.find(m => m.id === p.carModelId)
      grouped.set(key, {
        extractedCode: p.extractedCode ?? null,
        displayName: p.name,
        processIds: [p.id],
        carModels: cm ? [{ id: cm.id, name: cm.name, color: cm.color }] : [],
        workerId: p.workerId,
        workerName: p.workerName,
      })
    } else {
      const g = grouped.get(key)!
      g.processIds.push(p.id)
      const cm = cmStore.activeCarModels.find(m => m.id === p.carModelId)
      if (cm && !g.carModels.some(x => x.id === cm.id)) {
        g.carModels.push({ id: cm.id, name: cm.name, color: cm.color })
      }
      // Keep first non-null worker assignment
      if (!g.workerId && p.workerId) {
        g.workerId   = p.workerId
        g.workerName = p.workerName
      }
    }
  }
  return [...grouped.values()]
})

const unassignedCount = computed(() => controlPlanGroups.value.filter(g => !g.workerId).length)

// ─── Inline assign worker ─────────────────────────────────────────────────────
const assignTarget = ref<ControlPlanGroup | null>(null)
const workerSearch = ref('')

const allWorkersList = ref<Worker[]>([])

watch(assignTarget, async (v) => {
  if (v) {
    allWorkersList.value = await workersStore.fetchAll()
    workerSearch.value = ''
  }
})

const filteredWorkers = computed(() => {
  const q = workerSearch.value.toLowerCase()
  if (!q) return allWorkersList.value
  return allWorkersList.value.filter(w =>
    w.name.toLowerCase().includes(q) || w.workerId.toLowerCase().includes(q),
  )
})

async function doAssign(group: ControlPlanGroup, workerId: string | null) {
  try {
    // Assign to all active processes in the SAME station that share the extractedCode
    // (covers all car model variants of that control plan within this station only)
    const processIds = group.extractedCode
      ? stStore.allProcesses
          .filter(p =>
            p.extractedCode === group.extractedCode &&
            p.status === 'active' &&
            p.stationId === selectedStationId.value,
          )
          .map(p => p.id)
      : group.processIds

    await workersStore.assignWorker(processIds, workerId)
    toast(workerId ? 'Worker assigned!' : 'Assignment removed', workerId ? 'success' : 'warning')
    assignTarget.value = null

    // Refresh left panel + right panel
    await Promise.all([
      selectedLineId.value ? stStore.fetchStations(selectedLineId.value) : Promise.resolve(),
      workersStore.fetchWorkers(),
    ])
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Right panel: worker list ─────────────────────────────────────────────────
const workerPanelSearch = ref('')
const filteredPanelWorkers = computed(() => {
  const q = workerPanelSearch.value.toLowerCase()
  if (!q) return workersStore.workers
  return workersStore.workers.filter(w =>
    w.name.toLowerCase().includes(q) || w.workerId.toLowerCase().includes(q),
  )
})

// ─── Worker CRUD (right panel) ────────────────────────────────────────────────
const showAddWorker   = ref(false)
const editWorkerTarget = ref<Worker | null>(null)
const deleteWorkerTarget = ref<Worker | null>(null)
const workerForm      = ref({ name: '', workerId: '' })
const workerLoading   = ref(false)

function openAddWorker() {
  workerForm.value  = { name: '', workerId: '' }
  showAddWorker.value = true
}

function openEditWorker(w: Worker) {
  editWorkerTarget.value = w
  workerForm.value = { name: w.name, workerId: w.workerId }
}

async function saveWorker() {
  if (!workerForm.value.name.trim())     { toast('Name is required', 'error'); return }
  if (!workerForm.value.workerId.trim()) { toast('Worker ID is required', 'error'); return }
  workerLoading.value = true
  try {
    if (editWorkerTarget.value) {
      await workersStore.updateWorker(editWorkerTarget.value.id, {
        name:     workerForm.value.name.trim(),
        workerId: workerForm.value.workerId.trim(),
      })
      toast('Worker updated!')
      editWorkerTarget.value = null
    } else {
      await workersStore.createWorker(
        workerForm.value.name.trim(),
        workerForm.value.workerId.trim(),
      )
      toast('Worker added!')
      showAddWorker.value = false
    }
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { workerLoading.value = false }
}

async function doDeleteWorker() {
  if (!deleteWorkerTarget.value) return
  try {
    await workersStore.deleteWorker(deleteWorkerTarget.value.id)
    toast('Worker deleted', 'warning')
    deleteWorkerTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}
</script>

<template>
  <div class="p-8 h-full flex flex-col">
    <div class="flex items-start justify-between mb-5">
      <PageHeader
        title="Worker Assignment"
        :subtitle="`${workersStore.workers.length} worker(s) · ${unassignedCount} unassigned control plan(s)`"/>
    </div>

    <!-- Two-panel resizable layout -->
    <div ref="containerRef" class="flex flex-1 gap-0 min-h-0 overflow-hidden rounded-2xl border border-surface-700"
         :class="isDragging ? 'select-none cursor-col-resize' : ''">

      <!-- ── LEFT PANEL: control plans ─────────────────────────────────────── -->
      <div class="flex flex-col min-w-0 overflow-hidden bg-surface-950"
           :style="{ width: leftWidthPct + '%' }">

        <!-- Line + Station selectors -->
        <div class="flex items-center gap-3 px-5 py-3 border-b border-surface-700 flex-shrink-0 flex-wrap">
          <!-- Line selector -->
          <div class="relative">
            <select v-model="selectedLineId"
              class="appearance-none bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
              <option v-for="l in linesStore.lines" :key="l.id" :value="l.id">{{ l.name }}</option>
            </select>
            <ChevronDown :size="12" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>

          <!-- Station selector -->
          <div class="relative">
            <select v-model="selectedStationId"
              :disabled="lineStations.length === 0"
              class="appearance-none bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer disabled:opacity-50">
              <option v-for="s in lineStations" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <ChevronDown :size="12" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>

          <!-- Stats -->
          <div class="ml-auto flex items-center gap-4 text-xs">
            <span class="text-surface-300">Total: <strong class="text-slate-200">{{ controlPlanGroups.length }}</strong></span>
            <span v-if="unassignedCount" class="text-amber-400 flex items-center gap-1">
              <AlertCircle :size="12"/>
              <strong>{{ unassignedCount }}</strong> unassigned
            </span>
          </div>
        </div>

        <!-- Control plan groups list -->
        <div class="flex-1 overflow-y-auto p-4 space-y-2">
          <template v-if="loading">
            <div v-for="i in 6" :key="i" class="animate-pulse bg-surface-800 rounded-xl h-16 border border-surface-700"/>
          </template>
          <template v-else-if="!selectedStationId">
            <div class="text-center py-16 text-surface-400 text-sm">Select a line and station to view control plans</div>
          </template>
          <template v-else-if="controlPlanGroups.length === 0">
            <div class="text-center py-16 text-surface-400 text-sm">No active control plans for this station</div>
          </template>
          <template v-else>
            <div v-for="group in controlPlanGroups" :key="group.extractedCode ?? group.processIds[0]"
              :class="['flex items-center gap-3 bg-surface-900 rounded-xl px-4 py-3 border transition-all',
                       group.workerId ? 'border-surface-700' : 'border-amber-500/30']">

              <!-- Status dot -->
              <div :class="['w-2 h-2 rounded-full flex-shrink-0', group.workerId ? 'bg-green-400' : 'bg-amber-400']"/>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-100 truncate">{{ group.displayName }}</div>
                <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                  <span v-if="group.extractedCode" class="text-[10px] font-mono text-surface-400">{{ group.extractedCode }}</span>
                  <!-- Car model badges -->
                  <span v-for="cm in group.carModels" :key="cm.id"
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold"
                    :style="{ background: cm.color + '22', color: cm.color }">
                    {{ cm.name }}
                  </span>
                  <span class="text-[10px] text-surface-500">{{ group.processIds.length }} variant(s)</span>
                </div>
              </div>

              <!-- Worker badge / assign button -->
              <div class="flex items-center gap-2 flex-shrink-0">
                <template v-if="group.workerName">
                  <div class="flex items-center gap-1.5 rounded-lg px-2.5 py-1
                               bg-green-600 text-white
                               dark:bg-green-500/10 dark:border dark:border-green-500/30">
                    <UserCheck :size="12" class="dark:text-green-400"/>
                    <span class="text-xs font-medium dark:text-green-300">{{ group.workerName }}</span>
                  </div>
                </template>
                <template v-else>
                  <div class="flex items-center gap-1.5 rounded-lg px-2.5 py-1
                               bg-amber-500 text-white
                               dark:bg-amber-500/10 dark:border dark:border-amber-500/30">
                    <UserX :size="12" class="dark:text-amber-400"/>
                    <span class="text-xs font-medium dark:text-amber-300">Unassigned</span>
                  </div>
                </template>
                <AppButton size="sm" variant="secondary" @click="assignTarget = group">
                  <User :size="12"/> Assign
                </AppButton>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- ── DIVIDER ────────────────────────────────────────────────────────── -->
      <div class="w-1.5 bg-surface-800 hover:bg-brand-500/40 cursor-col-resize flex-shrink-0 transition-colors"
           @mousedown="onDividerMouseDown"/>

      <!-- ── RIGHT PANEL: workers ───────────────────────────────────────────── -->
      <div class="flex flex-col min-w-0 overflow-hidden bg-surface-950 flex-1">

        <div class="flex items-center gap-2 px-4 py-3 border-b border-surface-700 flex-shrink-0">
          <span class="text-xs font-bold text-surface-300 uppercase tracking-wider flex-1">Workers</span>
          <AppButton size="sm" @click="openAddWorker"><Plus :size="13"/></AppButton>
        </div>

        <!-- Search -->
        <div class="px-4 pt-3 pb-2">
          <div class="relative">
            <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
            <input v-model="workerPanelSearch" placeholder="Search…"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
          </div>
        </div>

        <!-- Worker cards -->
        <div class="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
          <div v-if="filteredPanelWorkers.length === 0" class="text-center py-10 text-surface-400 text-xs">No workers</div>
          <div v-for="w in filteredPanelWorkers" :key="w.id"
            class="bg-surface-900 rounded-xl p-3 border border-surface-700">
            <div class="flex items-center gap-2 mb-2">
              <div class="w-7 h-7 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-300 flex-shrink-0">
                {{ w.name.charAt(0).toUpperCase() }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-xs font-bold text-slate-200 truncate">{{ w.name }}</div>
                <div class="text-[10px] font-mono text-surface-400">{{ w.workerId }}</div>
              </div>
              <div class="flex gap-1">
                <button @click="openEditWorker(w)" class="text-surface-400 hover:text-brand-400 transition-colors p-0.5">
                  <Pencil :size="12"/>
                </button>
                <button @click="deleteWorkerTarget = w" class="text-surface-400 hover:text-red-400 transition-colors p-0.5">
                  <Trash2 :size="12"/>
                </button>
              </div>
            </div>
            <!-- Assignment badges (active only) -->
            <div v-if="w.assignments.filter(a => a.processStatus === 'active').length > 0" class="flex flex-wrap gap-1">
              <span v-for="a in w.assignments.filter(a => a.processStatus === 'active')" :key="a.processId"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 bg-surface-700 rounded text-[10px] text-surface-300 border border-surface-600">
                <span>{{ a.processName }}</span>
                <span class="text-surface-500">·</span>
                <span class="font-medium">{{ a.carModelName }}</span>
              </span>
            </div>
            <div v-else class="text-[10px] text-surface-500 italic">No assignments</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Assign worker drawer/modal ──────────────────────────────────────── -->
    <AppModal :open="!!assignTarget"
      :title="`Assign Worker — ${assignTarget?.displayName ?? ''}`"
      @close="assignTarget = null">
      <div class="relative mb-3">
        <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
        <input v-model="workerSearch" placeholder="Search workers…"
          class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
      </div>

      <!-- Unassign -->
      <button @click="doAssign(assignTarget!, null)"
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium mb-1 border border-transparent hover:border-red-500/30 hover:bg-red-500/10 text-surface-300 hover:text-red-300 transition-all">
        <UserX :size="14"/>
        Remove assignment
      </button>

      <div class="space-y-1 max-h-72 overflow-y-auto pr-1">
        <button v-for="w in filteredWorkers" :key="w.id"
          @click="doAssign(assignTarget!, w.id)"
          :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all border',
                   assignTarget?.workerId === w.id
                     ? 'bg-brand-500/15 border-brand-500/40 text-brand-300'
                     : 'border-transparent text-slate-200 hover:bg-surface-800']">
          <div class="w-7 h-7 rounded-full bg-surface-700 flex items-center justify-center text-xs font-bold text-surface-200 flex-shrink-0">
            {{ w.name.charAt(0).toUpperCase() }}
          </div>
          <div class="flex-1 text-left min-w-0">
            <div class="font-semibold truncate">{{ w.name }}</div>
            <div class="text-[10px] text-surface-400 font-mono">{{ w.workerId }}</div>
          </div>
          <span class="text-[10px] text-surface-500">{{ w.assignedCount }} assigned</span>
          <UserCheck v-if="assignTarget?.workerId === w.id" :size="13" class="text-brand-400"/>
        </button>
      </div>

      <div class="flex justify-end mt-4">
        <AppButton variant="secondary" @click="assignTarget = null">Close</AppButton>
      </div>
    </AppModal>

    <!-- ── Add / Edit Worker modal ────────────────────────────────────────── -->
    <AppModal :open="showAddWorker || !!editWorkerTarget"
      :title="editWorkerTarget ? `Edit — ${editWorkerTarget.name}` : 'Add Worker'"
      @close="showAddWorker = false; editWorkerTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Full Name">
          <AppInput v-model="workerForm.name" placeholder="e.g. Ali Hassan"/>
        </FormField>
        <FormField label="Worker ID">
          <AppInput v-model="workerForm.workerId" placeholder="e.g. W-0042"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAddWorker = false; editWorkerTarget = null">Cancel</AppButton>
        <AppButton :disabled="workerLoading" @click="saveWorker">
          {{ workerLoading ? 'Saving…' : (editWorkerTarget ? 'Save Changes' : 'Add Worker') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Delete worker confirm ─────────────────────────────────────────── -->
    <ConfirmDialog
      :open="!!deleteWorkerTarget"
      title="Delete Worker"
      danger
      label="Delete"
      :message="`Delete worker &quot;${deleteWorkerTarget?.name}&quot;? All their assignments will be removed.`"
      @close="deleteWorkerTarget = null"
      @confirm="doDeleteWorker"/>
  </div>
</template>
