<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToolRequestsStore } from '@/stores/toolRequests'
import type { ApiToolRequest } from '@/stores/toolRequests'
import { useToolTypesStore, useToolsStore } from '@/stores/tools'
import type { ApiTool } from '@/stores/tools'
import { toolsService } from '@/services/tools.service'
import { useWorkersStore } from '@/stores/workers'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppButton    from '@/components/ui/AppButton.vue'
import AppModal     from '@/components/ui/AppModal.vue'
import AppInput     from '@/components/ui/AppInput.vue'
import FormField    from '@/components/ui/FormField.vue'
import PageHeader    from '@/components/ui/PageHeader.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import {
  AlertTriangle, ChevronDown, RefreshCw, Search,
  Check, X, Wrench, Clock, User, Tag, CheckCircle2,
  CircleAlert, Loader2,
} from 'lucide-vue-next'

const store          = useToolRequestsStore()
const toolTypesStore = useToolTypesStore()
const toolsStore     = useToolsStore()
const workersStore   = useWorkersStore()
const auth           = useAuthStore()
const { toast }      = useToast()

const isPM = computed(() => auth.isPM)

// ─── Filter ───────────────────────────────────────────────────────────────────
const filterStatus = ref('')
async function applyFilter() {
  await store.fetchRequests({ status: filterStatus.value || undefined, page: 1 })
}

// ─── Submit Report form ───────────────────────────────────────────────────────
const reportForm = ref({
  reportedToolId: '',
  typeId: '',
  workerId: '',
  notes: '',
})

// ─── Tool ID lookup ───────────────────────────────────────────────────────────
type LookupState = 'idle' | 'loading' | 'found' | 'not_found'
const lookupState  = ref<LookupState>('idle')
const foundTool    = ref<ApiTool | null>(null)
let lookupTimeout: ReturnType<typeof setTimeout> | null = null

watch(() => reportForm.value.reportedToolId, (val) => {
  if (lookupTimeout) clearTimeout(lookupTimeout)
  if (!val.trim()) {
    lookupState.value = 'idle'
    foundTool.value   = null
    reportForm.value.typeId   = ''
    reportForm.value.workerId = ''
    return
  }
  lookupState.value = 'loading'
  lookupTimeout = setTimeout(async () => {
    try {
      const all = await toolsService.listAll()
      const match = all.find(t => t.toolId.toLowerCase() === val.trim().toLowerCase())
      if (match) {
        foundTool.value   = match
        lookupState.value = 'found'
        // Auto-fill type and worker from the found tool
        reportForm.value.typeId   = match.typeId
        reportForm.value.workerId = match.workerId || ''
      } else {
        foundTool.value   = null
        lookupState.value = 'not_found'
        // Clear auto-filled values so user can enter manually
        reportForm.value.typeId   = ''
        reportForm.value.workerId = ''
      }
    } catch {
      lookupState.value = 'idle'
    }
  }, 500)
})

const reportLoading  = ref(false)
const reportExpanded = ref(true)

async function submitReport() {
  if (!reportForm.value.reportedToolId.trim()) { toast('Tool ID is required', 'error'); return }
  if (!reportForm.value.typeId)                { toast('Tool type is required', 'error'); return }
  reportLoading.value = true
  try {
    const r = await store.createRequest({
      reportedToolId: reportForm.value.reportedToolId.trim(),
      typeId:         reportForm.value.typeId,
      workerId:       reportForm.value.workerId || null,
      notes:          reportForm.value.notes.trim() || null,
    })
    toast('Fault report submitted!')
    reportForm.value = { reportedToolId: '', typeId: '', workerId: '', notes: '' }
    lookupState.value = 'idle'
    foundTool.value   = null
    reportExpanded.value = false
    if (!r.faultyToolRef) {
      toast(`Tool "${r.reportedToolId}" not in system — PM will register it`, 'warning')
    }
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    reportLoading.value = false
  }
}

// ─── Mark Faulty modal (PM) ───────────────────────────────────────────────────
const showMarkFaulty  = ref(false)
const faultyTarget    = ref<ApiToolRequest | null>(null)
const faultyNote      = ref('')
const faultyLoading   = ref(false)

function openMarkFaulty(r: ApiToolRequest) {
  faultyTarget.value   = r
  faultyNote.value     = ''
  showMarkFaulty.value = true
}

async function doMarkFaulty() {
  if (!faultyTarget.value) return
  faultyLoading.value = true
  try {
    const updated = await store.markFaulty(faultyTarget.value.id, faultyNote.value || undefined)
    const label = updated.faultyToolRef
      ? `"${updated.faultyToolRef}" marked faulty`
      : `"${updated.reportedToolId}" registered & marked faulty`
    toast(label)
    showMarkFaulty.value = false
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    faultyLoading.value = false
  }
}

// ─── Resolve modal (PM) ───────────────────────────────────────────────────────
const showResolve    = ref(false)
const resolveTarget  = ref<ApiToolRequest | null>(null)
const resolveForm    = ref({ replacementToolId: '', note: '' })
const resolveLoading = ref(false)

const availableTools = computed(() =>
  toolsStore.tools.filter(t => t.status === 'available'),
)

function openResolve(r: ApiToolRequest) {
  resolveTarget.value = r
  resolveForm.value   = { replacementToolId: '', note: '' }
  showResolve.value   = true
}

async function doResolve() {
  if (!resolveTarget.value) return
  resolveLoading.value = true
  try {
    await store.resolve(resolveTarget.value.id, {
      replacementToolId: resolveForm.value.replacementToolId || null,
      note:              resolveForm.value.note.trim() || null,
    })
    toast('Request resolved!')
    showResolve.value = false
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    resolveLoading.value = false
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statusConfig(s: string) {
  return {
    pending:   { label: 'Pending',   dot: 'bg-amber-400',  badge: 'bg-amber-500 text-white dark:bg-amber-500/15 dark:text-amber-400 dark:border dark:border-amber-500/30' },
    in_review: { label: 'In Review', dot: 'bg-brand-400',  badge: 'bg-brand-500 text-white dark:bg-brand-500/15 dark:text-brand-400 dark:border dark:border-brand-500/30' },
    resolved:  { label: 'Resolved',  dot: 'bg-green-400',  badge: 'bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 dark:border dark:border-green-500/30' },
  }[s] ?? { label: s, dot: 'bg-surface-400', badge: 'bg-surface-700 text-surface-300' }
}

function fmtDate(d: string) {
  return new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

const pendingCount = computed(() => store.requests.filter(r => r.status === 'pending').length)
const reviewCount  = computed(() => store.requests.filter(r => r.status === 'in_review').length)

// ─── Init ─────────────────────────────────────────────────────────────────────
const pageLoading = ref(true)
onMounted(async () => {
  const base = [
    store.fetchRequests(),
    toolTypesStore.fetchTypes(),
    workersStore.fetchWorkers(),
  ]
  if (isPM.value) base.push(toolsStore.fetchTools({ status: 'available' }))
  try { await Promise.all(base) } finally { pageLoading.value = false }
})
</script>

<template>
  <div class="p-8 h-full flex flex-col">
    <div class="flex items-start justify-between mb-6">
      <PageHeader
        title="Tool Requests"
        :subtitle="isPM ? `${pendingCount} pending · ${reviewCount} in review` : `${store.total} request(s) submitted`"/>
      <button @click="store.fetchRequests({ status: filterStatus || undefined, page: 1 })"
        class="text-surface-400 hover:text-surface-200 transition-colors p-2 rounded-lg hover:bg-surface-800"
        title="Refresh">
        <RefreshCw :size="15"/>
      </button>
    </div>

    <div class="flex flex-1 gap-5 min-h-0 overflow-hidden">

      <!-- ── LEFT: Submit Report ─────────────────────────────────────────────── -->
      <div class="flex flex-col w-[38%] flex-shrink-0 bg-surface-950 rounded-2xl border border-surface-700 overflow-hidden">

        <!-- Header with collapse toggle -->
        <button
          @click="reportExpanded = !reportExpanded"
          class="flex items-center gap-3 px-5 py-4 border-b border-surface-700 hover:bg-surface-900 transition-colors text-left">
          <div class="w-8 h-8 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
            <AlertTriangle :size="15" class="text-amber-400"/>
          </div>
          <div class="flex-1">
            <div class="text-sm font-bold text-slate-200">Report Faulty Tool</div>
            <div class="text-xs text-surface-400">
              Reporting as <span class="text-slate-300 font-medium">{{ auth.currentUser?.name }}</span>
            </div>
          </div>
          <ChevronDown :size="15" :class="['text-surface-400 transition-transform', reportExpanded ? 'rotate-180' : '']"/>
        </button>

        <!-- Form -->
        <div v-if="reportExpanded" class="flex-1 overflow-y-auto p-5 space-y-4">

          <!-- Tool ID with live lookup -->
          <FormField label="Tool ID *">
            <div class="relative">
              <AppInput
                v-model="reportForm.reportedToolId"
                placeholder="e.g. DRILL-007"
                @keyup.enter="submitReport"/>
              <div class="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 v-if="lookupState === 'loading'"  :size="13" class="animate-spin text-surface-400"/>
                <Check   v-else-if="lookupState === 'found'"     :size="13" class="text-green-400"/>
                <X       v-else-if="lookupState === 'not_found'" :size="13" class="text-amber-400"/>
              </div>
            </div>

            <!-- Found: show tool details inline -->
            <div v-if="lookupState === 'found' && foundTool"
              class="mt-2 px-3 py-2.5 bg-green-500/8 border border-green-500/25 rounded-lg space-y-1">
              <div class="flex items-center gap-1.5 text-[10px] font-bold text-green-400 uppercase tracking-wider">
                <Check :size="10"/> Tool found in system
              </div>
              <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                <div class="text-surface-400">Type</div>
                <div class="font-medium text-slate-200">{{ foundTool.typeName }}</div>
                <div class="text-surface-400">Status</div>
                <div :class="['font-medium', foundTool.status === 'available' ? 'text-green-400' : foundTool.status === 'assigned' ? 'text-brand-400' : 'text-red-400']">
                  {{ foundTool.status.replace('_', ' ') }}
                </div>
                <template v-if="foundTool.workerName">
                  <div class="text-surface-400">Assigned to</div>
                  <div class="font-medium text-slate-200">{{ foundTool.workerName }}</div>
                </template>
              </div>
            </div>

            <!-- Not found -->
            <div v-else-if="lookupState === 'not_found'"
              class="mt-2 px-3 py-2 bg-amber-500/8 border border-amber-500/25 rounded-lg">
              <div class="flex items-center gap-1.5 text-xs text-amber-400">
                <AlertTriangle :size="11"/>
                Not registered in system — select type manually so PM can register it
              </div>
            </div>
          </FormField>

          <!-- Tool Type — locked when found, editable when not -->
          <FormField label="Tool Type *">
            <template v-if="lookupState === 'found' && foundTool">
              <div class="flex items-center gap-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm text-slate-300">
                <Tag :size="12" class="text-surface-500"/>
                {{ foundTool.typeName }}
              </div>
            </template>
            <template v-else>
              <div class="relative">
                <select v-model="reportForm.typeId"
                  class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
                  <option value="" disabled>Select type…</option>
                  <option v-for="tt in toolTypesStore.types" :key="tt.id" :value="tt.id">
                    {{ tt.name }}
                  </option>
                </select>
                <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
              </div>
            </template>
          </FormField>

          <!-- Worker — locked when found, editable when not -->
          <FormField label="Worker (who had the tool)">
            <template v-if="lookupState === 'found' && foundTool && foundTool.workerName">
              <div class="flex items-center gap-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm text-slate-300">
                <User :size="12" class="text-surface-500"/>
                {{ foundTool.workerName }}
              </div>
            </template>
            <template v-else>
              <div class="relative">
                <select v-model="reportForm.workerId"
                  class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
                  <option value="">Unknown / Not assigned</option>
                  <option v-for="w in workersStore.workers" :key="w.id" :value="w.id">
                    {{ w.name }} ({{ w.workerId }})
                  </option>
                </select>
                <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
              </div>
            </template>
          </FormField>

          <FormField label="Issue Description">
            <textarea
              v-model="reportForm.notes"
              placeholder="Describe what's wrong with the tool…"
              rows="3"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500 resize-none"/>
          </FormField>

          <AppButton class="w-full" :disabled="reportLoading || lookupState === 'loading'" @click="submitReport">
            <AlertTriangle :size="14"/>
            {{ reportLoading ? 'Submitting…' : 'Submit Report' }}
          </AppButton>
        </div>

        <div v-else class="flex-1 flex items-center justify-center text-surface-500 text-sm p-5 text-center">
          Click above to expand and submit a new fault report.
        </div>
      </div>

      <!-- ── RIGHT: Requests Queue ───────────────────────────────────────────── -->
      <div class="flex flex-col flex-1 min-w-0 bg-surface-950 rounded-2xl border border-surface-700 overflow-hidden">

        <!-- Toolbar -->
        <div class="flex items-center gap-3 px-5 py-3 border-b border-surface-700 flex-shrink-0">
          <span class="text-xs font-bold text-surface-300 uppercase tracking-wider flex-1">
            {{ isPM ? 'All Requests' : 'My Requests' }}
          </span>
          <span class="text-xs text-surface-500">{{ store.total }} total</span>
          <div class="relative">
            <select v-model="filterStatus" @change="applyFilter"
              class="appearance-none bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-7 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-brand-500 cursor-pointer">
              <option value="">All status</option>
              <option value="pending">Pending</option>
              <option value="in_review">In Review</option>
              <option value="resolved">Resolved</option>
            </select>
            <ChevronDown :size="11" class="absolute right-2 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
        </div>

        <!-- List -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <SkeletonTable v-if="pageLoading" :rows="8" :cols="3"/>
          <div v-else-if="store.requests.length === 0" class="flex flex-col items-center justify-center h-full text-center py-20">
            <CheckCircle2 :size="40" class="text-surface-600 mb-3"/>
            <p class="text-surface-400 text-sm">No requests found</p>
          </div>

          <div v-else v-for="r in store.requests" :key="r.id"
            :class="['bg-surface-900 rounded-xl border overflow-hidden',
                     r.status === 'pending'   ? 'border-amber-500/30' :
                     r.status === 'in_review' ? 'border-brand-500/30' :
                                                'border-surface-700']">

            <!-- Card header -->
            <div class="flex items-start gap-3 px-4 py-3 border-b border-surface-800">
              <div :class="['w-2 h-2 rounded-full mt-1.5 flex-shrink-0', statusConfig(r.status).dot]"/>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-bold text-slate-200 font-mono">{{ r.reportedToolId }}</span>
                  <span :class="['text-[10px] font-bold px-1.5 py-0.5 rounded', statusConfig(r.status).badge]">
                    {{ statusConfig(r.status).label }}
                  </span>
                  <span v-if="!r.toolDbId && r.status === 'pending'"
                    class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
                    Not in system
                  </span>
                </div>
                <div class="flex items-center gap-3 mt-1 flex-wrap text-[10px] text-surface-400">
                  <span class="flex items-center gap-1"><Tag :size="9"/> {{ r.typeName }}</span>
                  <span v-if="r.workerName" class="flex items-center gap-1">
                    <User :size="9"/> {{ r.workerName }} · {{ r.workerExternalId }}
                  </span>
                  <span class="flex items-center gap-1"><Clock :size="9"/> {{ fmtDate(r.createdAt) }}</span>
                </div>
              </div>

              <!-- PM Actions -->
              <div v-if="isPM && r.status !== 'resolved'" class="flex items-center gap-1.5 flex-shrink-0">
                <AppButton size="sm" variant="secondary" @click="openMarkFaulty(r)">
                  <CircleAlert :size="12"/>
                  {{ r.toolDbId ? 'Mark Faulty' : 'Register & Faulty' }}
                </AppButton>
                <AppButton size="sm" @click="openResolve(r)">
                  <CheckCircle2 :size="12"/> Resolve
                </AppButton>
              </div>

              <div v-else-if="r.status === 'resolved'" class="flex-shrink-0">
                <span class="flex items-center gap-1 text-[10px] text-green-400">
                  <Check :size="11"/> Resolved
                </span>
              </div>
            </div>

            <!-- Card body -->
            <div class="px-4 py-2.5 space-y-1">
              <div class="text-[10px] text-surface-500">
                Reported by <span class="text-surface-300 font-medium">{{ r.reporterName }}</span>
              </div>
              <div v-if="r.notes" class="text-xs text-surface-300">
                <span class="text-surface-500">Issue: </span>{{ r.notes }}
              </div>
              <div v-if="r.replacementToolRef"
                class="flex items-center gap-1.5 text-[10px] text-green-400">
                <Wrench :size="10"/>
                Replacement: <span class="font-mono font-bold">{{ r.replacementToolRef }}</span>
              </div>
              <div v-if="r.resolvedNote" class="text-[10px] text-surface-400 italic">
                {{ r.resolvedNote }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Mark Faulty Modal ───────────────────────────────────────────────── -->
    <AppModal
      :open="showMarkFaulty"
      :title="faultyTarget?.toolDbId ? `Mark Faulty — ${faultyTarget?.reportedToolId}` : `Register & Mark Faulty — ${faultyTarget?.reportedToolId}`"
      @close="showMarkFaulty = false">

      <div v-if="faultyTarget" class="mb-4 p-3 bg-surface-900 rounded-xl border border-surface-700 text-sm">
        <div v-if="!faultyTarget.toolDbId"
          class="flex items-start gap-2 text-amber-400 mb-2">
          <AlertTriangle :size="14" class="mt-0.5 flex-shrink-0"/>
          <span class="text-xs">
            <strong class="font-mono">{{ faultyTarget.reportedToolId }}</strong> is not in the system.
            It will be registered as <strong>{{ faultyTarget.typeName }}</strong> and immediately marked faulty.
          </span>
        </div>
        <div v-else class="text-xs text-surface-300">
          <strong class="font-mono">{{ faultyTarget.faultyToolRef }}</strong> will be marked faulty
          and unassigned from any worker.
        </div>
      </div>

      <FormField label="Note (optional)">
        <AppInput v-model="faultyNote" placeholder="Reason or additional details…" @keyup.enter="doMarkFaulty"/>
      </FormField>

      <div class="flex gap-3 justify-end mt-5">
        <AppButton variant="secondary" @click="showMarkFaulty = false">Cancel</AppButton>
        <AppButton variant="danger" :disabled="faultyLoading" @click="doMarkFaulty">
          <CircleAlert :size="13"/>
          {{ faultyLoading ? 'Processing…' : (faultyTarget?.toolDbId ? 'Mark Faulty' : 'Register & Mark Faulty') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Resolve Modal ──────────────────────────────────────────────────── -->
    <AppModal :open="showResolve"
      :title="`Resolve — ${resolveTarget?.reportedToolId}`"
      @close="showResolve = false">

      <p class="text-xs text-surface-400 mb-4">
        Optionally assign a replacement tool to the worker, then close the request.
      </p>

      <div class="space-y-4 mb-5">
        <FormField label="Replacement Tool (optional)">
          <div v-if="availableTools.length === 0" class="text-xs text-surface-500 italic py-2">
            No available tools in inventory.
          </div>
          <div v-else class="relative">
            <select v-model="resolveForm.replacementToolId"
              class="appearance-none w-full bg-surface-800 border border-surface-600 rounded-lg pl-3 pr-8 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
              <option value="">No replacement</option>
              <option v-for="t in availableTools" :key="t.id" :value="t.id">
                {{ t.toolId }} — {{ t.typeName }}
              </option>
            </select>
            <ChevronDown :size="13" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none"/>
          </div>
          <p v-if="resolveForm.replacementToolId && resolveTarget?.workerName"
            class="text-[10px] text-green-400 mt-1 flex items-center gap-1">
            <Check :size="10"/>
            Will be assigned to {{ resolveTarget.workerName }}
          </p>
        </FormField>

        <FormField label="Resolution Note (optional)">
          <AppInput v-model="resolveForm.note" placeholder="e.g. Replacement assigned, tool sent for repair…"/>
        </FormField>
      </div>

      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showResolve = false">Cancel</AppButton>
        <AppButton :disabled="resolveLoading" @click="doResolve">
          <CheckCircle2 :size="13"/>
          {{ resolveLoading ? 'Resolving…' : 'Mark Resolved' }}
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
