<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToolsStore, useToolTypesStore } from '@/stores/tools'
import type { ApiTool, ApiToolType } from '@/stores/tools'
import { toolsService } from '@/services/tools.service'
import { useToast } from '@/composables/useToast'
import AppCard      from '@/components/ui/AppCard.vue'
import AppButton    from '@/components/ui/AppButton.vue'
import AppModal     from '@/components/ui/AppModal.vue'
import AppInput     from '@/components/ui/AppInput.vue'
import FormField    from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import {
  Plus, Search, Package, Wrench, Pencil, Trash2, Clock, AlertTriangle,
  CheckCircle, RefreshCw, ChevronDown, Tag, X, Settings,
} from 'lucide-vue-next'

const toolsStore     = useToolsStore()
const toolTypesStore = useToolTypesStore()
const { toast }      = useToast()

// ─── Left-panel sub-tabs ─────────────────────────────────────────────────────
type LeftTab = 'detail' | 'types'
const leftTab = ref<LeftTab>('detail')

// ─── Right panel filters ──────────────────────────────────────────────────────
const searchInput  = ref('')
const filterTypeId = ref('')
const filterStatus = ref('')

let searchTimeout: ReturnType<typeof setTimeout> | null = null
watch(searchInput, (val) => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    toolsStore.fetchTools({ search: val || undefined, typeId: filterTypeId.value || undefined, status: filterStatus.value || undefined, page: 1 })
  }, 350)
})
watch([filterTypeId, filterStatus], () => {
  toolsStore.fetchTools({ search: searchInput.value || undefined, typeId: filterTypeId.value || undefined, status: filterStatus.value || undefined, page: 1 })
})

// ─── Selected tool (detail panel) ────────────────────────────────────────────
const selectedTool = ref<ApiTool | null>(null)
const detailLoading = ref(false)

async function selectTool(t: ApiTool) {
  detailLoading.value = true
  try {
    selectedTool.value = await toolsService.get(t.id)
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    detailLoading.value = false
  }
}

// ─── Add / Edit Tool modal ────────────────────────────────────────────────────
const showAdd     = ref(false)
const editTarget  = ref<ApiTool | null>(null)
const toolForm    = ref({ toolId: '', typeId: '', notes: '' })
const toolLoading = ref(false)

function openAdd() {
  toolForm.value = { toolId: '', typeId: toolTypesStore.types[0]?.id ?? '', notes: '' }
  showAdd.value = true
}

function openEdit(t: ApiTool) {
  editTarget.value = t
  toolForm.value = { toolId: t.toolId, typeId: t.typeId, notes: t.notes ?? '' }
}

async function saveTool() {
  if (!toolForm.value.toolId.trim()) { toast('Tool ID is required', 'error'); return }
  if (!toolForm.value.typeId)        { toast('Tool type is required', 'error'); return }
  toolLoading.value = true
  try {
    if (editTarget.value) {
      const updated = await toolsStore.updateTool(editTarget.value.id, {
        toolId: toolForm.value.toolId.trim(),
        notes:  toolForm.value.notes || undefined,
      })
      if (selectedTool.value?.id === editTarget.value.id) {
        selectedTool.value = await toolsService.get(updated.id)
      }
      toast('Tool updated!')
      editTarget.value = null
    } else {
      const created = await toolsStore.createTool({
        toolId: toolForm.value.toolId.trim(),
        typeId: toolForm.value.typeId,
        notes:  toolForm.value.notes || undefined,
      })
      toast(`Tool "${toolForm.value.toolId}" added!`)
      showAdd.value = false
      await selectTool(created)
    }
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { toolLoading.value = false }
}

// ─── Delete tool ──────────────────────────────────────────────────────────────
const deleteTarget = ref<ApiTool | null>(null)

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    if (selectedTool.value?.id === deleteTarget.value.id) selectedTool.value = null
    await toolsStore.deleteTool(deleteTarget.value.id)
    toast('Tool deleted', 'warning')
    deleteTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Change Status modal ──────────────────────────────────────────────────────
const showStatus  = ref(false)
const statusForm  = ref({ status: 'available', note: '' })
const statusLoading = ref(false)

function openStatus(t: ApiTool) {
  statusForm.value = { status: t.status === 'assigned' ? 'available' : t.status, note: '' }
  showStatus.value = true
}

async function saveStatus() {
  if (!selectedTool.value) return
  statusLoading.value = true
  try {
    const updated = await toolsStore.setStatus(selectedTool.value.id, statusForm.value.status, statusForm.value.note || undefined)
    selectedTool.value = await toolsService.get(updated.id)
    toast('Status updated!')
    showStatus.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { statusLoading.value = false }
}

// Quick status from list card
async function quickStatus(t: ApiTool, status: string) {
  try {
    const updated = await toolsStore.setStatus(t.id, status)
    if (selectedTool.value?.id === t.id) {
      selectedTool.value = await toolsService.get(updated.id)
    }
    toast(`Marked ${status.replace('_', ' ')}`)
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Assign modal ─────────────────────────────────────────────────────────────
const showAssign   = ref(false)
const assignForm   = ref({ workerId: '', processId: '' })
const assignLoading = ref(false)

function openAssign() {
  assignForm.value = { workerId: selectedTool.value?.workerId ?? '', processId: selectedTool.value?.processId ?? '' }
  showAssign.value = true
}

async function saveAssign() {
  if (!selectedTool.value) return
  assignLoading.value = true
  try {
    const updated = await toolsStore.assignTool(selectedTool.value.id, {
      workerId:  assignForm.value.workerId  || null,
      processId: assignForm.value.processId || null,
    })
    selectedTool.value = await toolsService.get(updated.id)
    toast('Assignment updated!')
    showAssign.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { assignLoading.value = false }
}

// ─── Tool Types CRUD ──────────────────────────────────────────────────────────
const typeForm    = ref({ name: '', maxPerWorker: 1 })
const typeLoading = ref(false)
const editTypeTarget = ref<ApiToolType | null>(null)
const deleteTypeTarget = ref<ApiToolType | null>(null)
const showAddType = ref(false)

function openAddType() {
  typeForm.value = { name: '', maxPerWorker: 1 }
  editTypeTarget.value = null
  showAddType.value = true
}

function openEditType(tt: ApiToolType) {
  editTypeTarget.value = tt
  typeForm.value = { name: tt.name, maxPerWorker: tt.maxPerWorker }
  showAddType.value = true
}

async function saveType() {
  if (!typeForm.value.name.trim()) { toast('Name is required', 'error'); return }
  typeLoading.value = true
  try {
    if (editTypeTarget.value) {
      await toolTypesStore.updateType(editTypeTarget.value.id, {
        name: typeForm.value.name.trim(),
        maxPerWorker: typeForm.value.maxPerWorker,
      })
      toast('Tool type updated!')
    } else {
      await toolTypesStore.createType(typeForm.value.name.trim(), typeForm.value.maxPerWorker)
      toast('Tool type created!')
    }
    showAddType.value = false
    editTypeTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { typeLoading.value = false }
}

async function doDeleteType() {
  if (!deleteTypeTarget.value) return
  try {
    await toolTypesStore.deleteType(deleteTypeTarget.value.id)
    toast('Tool type deleted', 'warning')
    deleteTypeTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusColor(s: string) {
  return {
    available: 'bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 dark:border dark:border-green-500/30',
    assigned:  'bg-brand-500 text-white dark:bg-brand-500/15 dark:text-brand-400 dark:border dark:border-brand-500/30',
    faulty:    'bg-red-600 text-white dark:bg-red-500/15 dark:text-red-400 dark:border dark:border-red-500/30',
    in_repair: 'bg-amber-500 text-white dark:bg-amber-500/15 dark:text-amber-400 dark:border dark:border-amber-500/30',
  }[s] ?? 'bg-surface-600 text-white dark:bg-surface-700 dark:text-surface-300'
}

function statusLabel(s: string) {
  return { available: 'Available', assigned: 'Assigned', faulty: 'Faulty', in_repair: 'In Repair' }[s] ?? s
}

function actionLabel(a: string) {
  return a.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function actionColor(a: string) {
  if (a.includes('faulty'))    return 'text-red-400'
  if (a.includes('repair'))    return 'text-amber-400'
  if (a.includes('available')) return 'text-green-400'
  if (a.includes('assigned'))  return 'text-brand-400'
  if (a.includes('unassign'))  return 'text-surface-400'
  return 'text-surface-300'
}

function fmtDate(d: string) {
  return new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

const sortedTools = computed(() => {
  return [...toolsStore.tools].sort((a, b) => {
    const order = { available: 0, assigned: 1, in_repair: 2, faulty: 3 }
    return (order[a.status] ?? 9) - (order[b.status] ?? 9) || a.toolId.localeCompare(b.toolId)
  })
})

// ─── Init ─────────────────────────────────────────────────────────────────────
const loading = ref(true)
onMounted(async () => {
  try { await Promise.all([toolsStore.fetchTools(), toolTypesStore.fetchTypes()]) }
  finally { loading.value = false }
})
</script>

<template>
  <div class="p-8 h-full flex flex-col">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <PageHeader title="Tool Management" :subtitle="`${toolsStore.total} tool(s) registered`"/>
      <div class="flex items-center gap-2">
        <button @click="toolsStore.fetchTools({ search: searchInput || undefined, typeId: filterTypeId || undefined, status: filterStatus || undefined })"
          class="text-surface-400 hover:text-surface-200 transition-colors p-2 rounded-lg hover:bg-surface-800" title="Refresh">
          <RefreshCw :size="15"/>
        </button>
        <AppButton @click="openAdd"><Plus :size="15"/> Add Tool</AppButton>
      </div>
    </div>

    <!-- Two-panel layout -->
    <div class="flex flex-1 gap-5 min-h-0 overflow-hidden">

      <!-- ── LEFT PANEL: detail / types ───────────────────────────────────── -->
      <div class="flex flex-col w-[58%] min-w-0 bg-surface-950 rounded-2xl border border-surface-700 overflow-hidden">

        <!-- Sub-tabs -->
        <div class="flex border-b border-surface-700 flex-shrink-0">
          <button v-for="tab in ([{ id: 'detail', label: 'Tool Detail', icon: Wrench }, { id: 'types', label: 'Tool Types', icon: Tag }] as const)"
            :key="tab.id"
            @click="leftTab = tab.id"
            :class="['flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors border-b-2',
                     leftTab === tab.id
                       ? 'text-brand-400 border-brand-500 bg-brand-500/5'
                       : 'text-surface-400 border-transparent hover:text-surface-200']">
            <component :is="tab.icon" :size="14"/>
            {{ tab.label }}
          </button>
        </div>

        <!-- ── DETAIL TAB ─────────────────────────────────────────────────── -->
        <div v-if="leftTab === 'detail'" class="flex-1 overflow-y-auto">
          <!-- Loading -->
          <div v-if="detailLoading" class="flex items-center justify-center h-32">
            <RefreshCw :size="20" class="animate-spin text-brand-400"/>
          </div>

          <!-- Empty state -->
          <div v-else-if="!selectedTool" class="flex flex-col items-center justify-center h-full text-center py-20">
            <Package :size="48" class="text-surface-600 mb-4"/>
            <p class="text-surface-400 text-sm">Select a tool from the list to view details</p>
          </div>

          <!-- Detail -->
          <div v-else class="p-5 space-y-5">
            <!-- Top bar: toolId + status -->
            <div class="flex items-start gap-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-1">
                  <span class="text-xl font-black text-slate-100 font-mono">{{ selectedTool.toolId }}</span>
                  <span :class="['px-2.5 py-0.5 rounded-full text-xs font-bold', statusColor(selectedTool.status)]">
                    {{ statusLabel(selectedTool.status) }}
                  </span>
                </div>
                <div class="flex items-center gap-2 text-sm text-surface-400">
                  <Tag :size="12"/>
                  <span>{{ selectedTool.typeName }}</span>
                </div>
              </div>
              <!-- Action buttons -->
              <div class="flex items-center gap-2 flex-shrink-0">
                <AppButton size="sm" variant="secondary" @click="openEdit(selectedTool)">
                  <Pencil :size="12"/> Edit
                </AppButton>
                <AppButton size="sm" variant="secondary" @click="openStatus(selectedTool)">
                  <Settings :size="12"/> Status
                </AppButton>
                <AppButton size="sm" variant="secondary" @click="openAssign">
                  <Wrench :size="12"/> Assign
                </AppButton>
                <AppButton size="sm" variant="danger" @click="deleteTarget = selectedTool">
                  <Trash2 :size="12"/>
                </AppButton>
              </div>
            </div>

            <!-- Assignment info -->
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-surface-900 rounded-xl p-4 border border-surface-700">
                <div class="text-xs font-bold text-surface-500 uppercase tracking-wider mb-2">Assigned Worker</div>
                <div v-if="selectedTool.workerName" class="text-sm font-semibold text-slate-200">{{ selectedTool.workerName }}</div>
                <div v-else class="text-sm text-surface-500 italic">Unassigned</div>
              </div>
              <!-- <div class="bg-surface-900 rounded-xl p-4 border border-surface-700">
                <div class="text-xs font-bold text-surface-500 uppercase tracking-wider mb-2">Control Plan</div>
                <div v-if="selectedTool.processName" class="text-sm font-semibold text-slate-200">{{ selectedTool.processName }}</div>
                <div v-else class="text-sm text-surface-500 italic">None</div>
              </div> -->
            </div>

            <!-- Notes -->
            <div v-if="selectedTool.notes" class="bg-surface-900 rounded-xl p-4 border border-surface-700">
              <div class="text-xs font-bold text-surface-500 uppercase tracking-wider mb-2">Notes</div>
              <p class="text-sm text-surface-200">{{ selectedTool.notes }}</p>
            </div>

            <!-- Event history -->
            <div>
              <div class="text-xs font-bold text-surface-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Clock :size="11"/>
                Event History
              </div>
              <div v-if="selectedTool.events.length === 0" class="text-sm text-surface-500 italic">No events yet.</div>
              <div v-else class="space-y-2">
                <div v-for="ev in selectedTool.events" :key="ev.id"
                  class="flex items-start gap-3 bg-surface-900 rounded-xl px-4 py-3 border border-surface-800">
                  <div :class="['w-2 h-2 rounded-full mt-1.5 flex-shrink-0', actionColor(ev.action).replace('text-', 'bg-')]"/>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                      <span :class="['text-xs font-bold', actionColor(ev.action)]">{{ actionLabel(ev.action) }}</span>
                      <span class="text-[10px] text-surface-500">{{ fmtDate(ev.createdAt) }}</span>
                    </div>
                    <div v-if="ev.workerName || ev.processName" class="text-xs text-surface-300">
                      <span v-if="ev.workerName">{{ ev.workerName }}</span>
                      <span v-if="ev.workerName && ev.processName"> · </span>
                      <span v-if="ev.processName">{{ ev.processName }}</span>
                    </div>
                    <div v-if="ev.note" class="text-xs text-surface-400 mt-0.5">{{ ev.note }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── TYPES TAB ──────────────────────────────────────────────────── -->
        <div v-else class="flex-1 overflow-y-auto p-5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-sm font-bold text-slate-200">{{ toolTypesStore.types.length }} type(s)</span>
            <AppButton size="sm" @click="openAddType"><Plus :size="13"/> Add Type</AppButton>
          </div>

          <div v-if="toolTypesStore.types.length === 0" class="text-center py-12">
            <Tag :size="32" class="mx-auto mb-3 text-surface-600"/>
            <p class="text-sm text-surface-400">No tool types yet</p>
          </div>

          <div v-else class="space-y-2">
            <div v-for="tt in toolTypesStore.types" :key="tt.id"
              class="flex items-center gap-3 bg-surface-900 rounded-xl px-4 py-3 border border-surface-700">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-slate-200">{{ tt.name }}</div>
                <div class="text-xs text-surface-400 mt-0.5">
                  Max {{ tt.maxPerWorker }} per worker · {{ tt.toolCount }} tool(s)
                </div>
              </div>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <button @click="openEditType(tt)"
                  class="text-surface-400 hover:text-brand-400 transition-colors p-1.5 rounded-lg hover:bg-surface-700">
                  <Pencil :size="13"/>
                </button>
                <button @click="deleteTypeTarget = tt"
                  class="text-surface-400 hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-surface-700">
                  <Trash2 :size="13"/>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── RIGHT PANEL: tool list ────────────────────────────────────────── -->
      <div class="flex flex-col flex-1 min-w-0 bg-surface-950 rounded-2xl border border-surface-700 overflow-hidden">

        <!-- Toolbar -->
        <div class="flex items-center gap-2 px-4 py-3 border-b border-surface-700 flex-shrink-0">
          <span class="text-xs font-bold text-surface-300 uppercase tracking-wider">Tools</span>
          <div class="flex-1"/>
          <AppButton size="sm" @click="openAdd"><Plus :size="13"/></AppButton>
        </div>

        <!-- Filters -->
        <div class="px-4 pt-3 pb-2 space-y-2 flex-shrink-0">
          <!-- Search -->
          <div class="relative">
            <Search :size="13" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
            <input v-model="searchInput" placeholder="Search by ID…"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
          </div>
          <!-- Type + Status dropdowns -->
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
          <template v-if="loading">
            <div v-for="i in 8" :key="i" class="animate-pulse bg-surface-700/50 rounded-xl h-14"/>
          </template>
          <div v-else-if="sortedTools.length === 0" class="text-center py-10 text-surface-400 text-xs">No tools found</div>
          <div v-else v-for="t in sortedTools" :key="t.id"
            @click="selectTool(t)"
            :class="['flex items-center gap-3 rounded-xl px-3 py-2.5 border cursor-pointer transition-all',
                     selectedTool?.id === t.id
                       ? 'bg-brand-500/10 border-brand-500/40'
                       : 'bg-surface-900 border-surface-700 hover:border-surface-500']">
            <!-- Status dot -->
            <div :class="['w-2 h-2 rounded-full flex-shrink-0',
                          { available: 'bg-green-400', assigned: 'bg-brand-400', faulty: 'bg-red-400', in_repair: 'bg-amber-400' }[t.status]]"/>
            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="text-xs font-bold text-slate-200 font-mono truncate">{{ t.toolId }}</div>
              <div class="flex items-center gap-1.5 mt-0.5">
                <span class="text-[10px] text-surface-400">{{ t.typeName }}</span>
                <span v-if="t.workerName" class="text-[10px] text-surface-500">· {{ t.workerName }}</span>
              </div>
            </div>
            <!-- Status badge -->
            <span :class="['px-1.5 py-0.5 rounded text-[10px] font-bold flex-shrink-0', statusColor(t.status)]">
              {{ statusLabel(t.status) }}
            </span>
            <!-- Quick actions -->
            <div class="flex gap-1 flex-shrink-0" @click.stop>
              <button v-if="t.status !== 'faulty'"
                @click="quickStatus(t, 'faulty')"
                title="Mark Faulty"
                class="text-surface-500 hover:text-red-400 transition-colors p-1 rounded hover:bg-surface-700">
                <AlertTriangle :size="11"/>
              </button>
              <button v-if="t.status !== 'available'"
                @click="quickStatus(t, 'available')"
                title="Mark Available"
                class="text-surface-500 hover:text-green-400 transition-colors p-1 rounded hover:bg-surface-700">
                <CheckCircle :size="11"/>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Add / Edit Tool modal ─────────────────────────────────────────────── -->
    <AppModal :open="showAdd || !!editTarget"
      :title="editTarget ? `Edit — ${editTarget.toolId}` : 'Add Tool'"
      @close="showAdd = false; editTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Tool ID">
          <AppInput v-model="toolForm.toolId" placeholder="e.g. DRL-001" @keyup.enter="saveTool"/>
        </FormField>
        <FormField v-if="!editTarget" label="Tool Type">
          <div class="relative">
            <select v-model="toolForm.typeId"
              class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
              <option value="" disabled>Select type…</option>
              <option v-for="tt in toolTypesStore.types" :key="tt.id" :value="tt.id">{{ tt.name }}</option>
            </select>
            <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
        </FormField>
        <FormField label="Notes (optional)">
          <AppInput v-model="toolForm.notes" placeholder="Any notes…"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAdd = false; editTarget = null">Cancel</AppButton>
        <AppButton :disabled="toolLoading" @click="saveTool">
          {{ toolLoading ? 'Saving…' : (editTarget ? 'Save Changes' : 'Add Tool') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Change Status modal ───────────────────────────────────────────────── -->
    <AppModal :open="showStatus" title="Change Tool Status" @close="showStatus = false">
      <div class="space-y-4 mb-5">
        <FormField label="Status">
          <div class="grid grid-cols-3 gap-2">
            <button v-for="s in ['available', 'faulty', 'in_repair']" :key="s"
              @click="statusForm.status = s"
              :class="['px-3 py-2 rounded-lg text-xs font-bold border transition-all',
                       statusForm.status === s ? statusColor(s) : 'border-surface-600 text-surface-400 hover:border-surface-500']">
              {{ statusLabel(s) }}
            </button>
          </div>
        </FormField>
        <FormField label="Note (optional)">
          <AppInput v-model="statusForm.note" placeholder="Reason for status change…"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showStatus = false">Cancel</AppButton>
        <AppButton :disabled="statusLoading" @click="saveStatus">
          {{ statusLoading ? 'Saving…' : 'Update Status' }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Assign modal ──────────────────────────────────────────────────────── -->
    <AppModal :open="showAssign" title="Update Assignment" @close="showAssign = false">
      <p class="text-xs text-surface-400 mb-4">
        Provide a worker ID or process ID to assign. Leave both empty to unassign.
      </p>
      <div class="space-y-4 mb-5">
        <FormField label="Worker ID (optional)">
          <AppInput v-model="assignForm.workerId" placeholder="Worker DB ID…"/>
        </FormField>
        <FormField label="Process ID (optional)">
          <AppInput v-model="assignForm.processId" placeholder="Process DB ID…"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAssign = false">Cancel</AppButton>
        <AppButton :disabled="assignLoading" @click="saveAssign">
          {{ assignLoading ? 'Saving…' : 'Update Assignment' }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Delete Tool confirm ───────────────────────────────────────────────── -->
    <ConfirmDialog
      :open="!!deleteTarget"
      title="Delete Tool"
      danger
      label="Delete"
      :message="`Delete tool &quot;${deleteTarget?.toolId}&quot;? All its event history will also be removed.`"
      @close="deleteTarget = null"
      @confirm="doDelete"/>

    <!-- ── Add / Edit Type modal ─────────────────────────────────────────────── -->
    <AppModal :open="showAddType"
      :title="editTypeTarget ? `Edit Type — ${editTypeTarget.name}` : 'Add Tool Type'"
      @close="showAddType = false; editTypeTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Type Name">
          <AppInput v-model="typeForm.name" placeholder="e.g. Drill" @keyup.enter="saveType"/>
        </FormField>
        <FormField label="Max Per Worker">
          <AppInput v-model.number="typeForm.maxPerWorker" type="number" placeholder="1"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAddType = false; editTypeTarget = null">Cancel</AppButton>
        <AppButton :disabled="typeLoading" @click="saveType">
          {{ typeLoading ? 'Saving…' : (editTypeTarget ? 'Save Changes' : 'Create Type') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Delete Type confirm ───────────────────────────────────────────────── -->
    <ConfirmDialog
      :open="!!deleteTypeTarget"
      title="Delete Tool Type"
      danger
      label="Delete"
      :message="`Delete type &quot;${deleteTypeTarget?.name}&quot;? This will fail if tools of this type exist.`"
      @close="deleteTypeTarget = null"
      @confirm="doDeleteType"/>
  </div>
</template>
