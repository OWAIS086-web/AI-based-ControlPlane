<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useWorkersStore } from '@/stores/workers'
import type { Worker }     from '@/stores/workers'
import { toolsService }    from '@/services/tools.service'
import type { ApiTool }    from '@/services/tools.service'
import { useToast }        from '@/composables/useToast'
import AppCard      from '@/components/ui/AppCard.vue'
import AppButton    from '@/components/ui/AppButton.vue'
import AppModal     from '@/components/ui/AppModal.vue'
import AppInput     from '@/components/ui/AppInput.vue'
import FormField    from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PageHeader    from '@/components/ui/PageHeader.vue'
import VrdPagination from '@/components/ui/VrdPagination.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import { Plus, Pencil, Trash2, Search, User, UserCheck, RefreshCw, Wrench } from 'lucide-vue-next'

const workersStore = useWorkersStore()
const { toast }    = useToast()

// ─── Filters ──────────────────────────────────────────────────────────────────
const searchInput = ref('')

let searchTimeout: ReturnType<typeof setTimeout> | null = null

watch(searchInput, (val) => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    workersStore.fetchWorkers({ search: val || undefined, page: 1 })
  }, 350)
})

async function refresh() {
  await workersStore.fetchWorkers({ search: searchInput.value || undefined, page: 1 })
}

// ─── Pagination ───────────────────────────────────────────────────────────────
const totalPages = computed(() =>
  Math.max(1, Math.ceil(workersStore.total / workersStore.limit)),
)

function onPageChange(p: number) {
  workersStore.fetchWorkers({ page: p })
}

function onPerPageChange(l: number) {
  workersStore.fetchWorkers({ limit: l, page: 1 })
}

// ─── Worker CRUD ──────────────────────────────────────────────────────────────
const showAdd      = ref(false)
const editTarget   = ref<Worker | null>(null)
const deleteTarget = ref<Worker | null>(null)
const form         = ref({ name: '', workerId: '' })
const formLoading  = ref(false)

function openAdd() {
  form.value = { name: '', workerId: '' }
  showAdd.value = true
}

function openEdit(w: Worker) {
  editTarget.value = w
  form.value = { name: w.name, workerId: w.workerId }
}

async function saveForm() {
  if (!form.value.name.trim())     { toast('Name is required', 'error'); return }
  if (!form.value.workerId.trim()) { toast('Worker ID is required', 'error'); return }
  formLoading.value = true
  try {
    if (editTarget.value) {
      await workersStore.updateWorker(editTarget.value.id, {
        name:     form.value.name.trim(),
        workerId: form.value.workerId.trim(),
      })
      toast('Worker updated!')
      editTarget.value = null
    } else {
      await workersStore.createWorker(form.value.name.trim(), form.value.workerId.trim())
      toast(`Worker "${form.value.name}" added!`)
      showAdd.value = false
    }
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { formLoading.value = false }
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await workersStore.deleteWorker(deleteTarget.value.id)
    toast('Worker deleted', 'warning')
    deleteTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Expanded row ─────────────────────────────────────────────────────────────
const expandedId  = ref<string | null>(null)
const workerTools = ref<Record<string, ApiTool[]>>({})

async function toggleExpand(id: string) {
  if (expandedId.value === id) {
    expandedId.value = null
    return
  }
  expandedId.value = id
  if (!workerTools.value[id]) {
    try {
      const all = await toolsService.listAll()
      workerTools.value = { ...workerTools.value, [id]: all.filter(t => t.workerId === id) }
    } catch {
      workerTools.value = { ...workerTools.value, [id]: [] }
    }
  }
}

function toolStatusColor(s: string) {
  return {
    available: 'bg-green-600 text-white dark:bg-green-500/15 dark:text-green-400 dark:border-green-500/30',
    assigned:  'bg-brand-500 text-white dark:bg-brand-500/15 dark:text-brand-400 dark:border-brand-500/30',
    faulty:    'bg-red-600 text-white dark:bg-red-500/15 dark:text-red-400 dark:border-red-500/30',
    in_repair: 'bg-amber-500 text-white dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30',
  }[s] ?? 'bg-surface-600 text-white dark:bg-surface-700 dark:text-surface-300'
}

function toolStatusLabel(s: string) {
  return { available: 'Available', assigned: 'Assigned', faulty: 'Faulty', in_repair: 'In Repair' }[s] ?? s
}

// ─── Init ─────────────────────────────────────────────────────────────────────
const loading = ref(true)
onMounted(async () => {
  try { await workersStore.fetchWorkers() } finally { loading.value = false }
})
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <PageHeader
        title="Worker Management"
        :subtitle="`${workersStore.total} worker(s) total`"/>
      <div class="flex items-center gap-2">
        <button @click="refresh"
          class="text-surface-400 hover:text-surface-200 transition-colors p-2 rounded-lg hover:bg-surface-800"
          title="Refresh">
          <RefreshCw :size="15"/>
        </button>
        <AppButton @click="openAdd"><Plus :size="15"/> Add Worker</AppButton>
      </div>
    </div>

    <!-- Filter bar -->
    <AppCard class="mb-5 !py-3 !px-4">
      <div class="relative">
        <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
        <input v-model="searchInput" placeholder="Search by name or worker ID…"
          class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
      </div>
    </AppCard>

    <!-- Empty state -->
    <AppCard v-if="loading" class="!p-0 overflow-hidden"><SkeletonTable :rows="7" :cols="4"/></AppCard>
    <AppCard v-else-if="workersStore.workers.length === 0" class="text-center py-16">
      <User :size="48" class="mx-auto mb-4 text-surface-400"/>
      <h3 class="text-lg font-bold text-slate-100 mb-2">No Workers Yet</h3>
      <p class="text-sm text-surface-200 mb-5">Add workers to start assigning them to control plans.</p>
      <AppButton @click="openAdd"><Plus :size="15"/> Add Worker</AppButton>
    </AppCard>

    <template v-else>
      <!-- Table -->
      <AppCard class="overflow-hidden !p-0 mb-4">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-surface-700">
              <th class="text-left px-5 py-3 text-xs font-bold text-surface-400 uppercase tracking-wider">Worker</th>
              <th class="text-left px-5 py-3 text-xs font-bold text-surface-400 uppercase tracking-wider">ID</th>
              <th class="text-left px-5 py-3 text-xs font-bold text-surface-400 uppercase tracking-wider">Assignments</th>
              <th class="px-5 py-3"/>
            </tr>
          </thead>
          <tbody>
            <template v-for="w in workersStore.workers" :key="w.id">
              <tr :class="['border-b border-surface-800 hover:bg-surface-800/50 transition-colors cursor-pointer',
                           expandedId === w.id ? 'bg-surface-800/40' : '']"
                  @click="toggleExpand(w.id)">
                <td class="px-5 py-3">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-300 flex-shrink-0">
                      {{ w.name.charAt(0).toUpperCase() }}
                    </div>
                    <span class="font-semibold text-slate-200">{{ w.name }}</span>
                  </div>
                </td>
                <td class="px-5 py-3 font-mono text-xs text-surface-300">{{ w.workerId }}</td>
                <td class="px-5 py-3">
                  <span v-if="w.assignedCount > 0"
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium
                           bg-green-600 text-white
                           dark:bg-green-500/10 dark:border dark:border-green-500/25 dark:text-green-300">
                    <UserCheck :size="11"/>
                    {{ w.assignedCount }} plan(s)
                  </span>
                  <span v-else class="text-xs text-surface-500 italic">Unassigned</span>
                </td>
                <td class="px-5 py-3">
                  <div class="flex items-center justify-end gap-2" @click.stop>
                    <AppButton size="sm" variant="secondary" @click="openEdit(w)">
                      <Pencil :size="12"/>
                    </AppButton>
                    <AppButton size="sm" variant="danger" @click="deleteTarget = w">
                      <Trash2 :size="12"/>
                    </AppButton>
                  </div>
                </td>
              </tr>

              <!-- Expanded: assignment + tool detail -->
              <tr v-if="expandedId === w.id" class="bg-surface-800/30 border-b border-surface-800">
                <td colspan="4" class="px-5 py-3 space-y-3">
                  <!-- Control plan assignments -->
                  <div>
                    <div class="text-[10px] font-bold text-surface-500 uppercase tracking-wider mb-1.5">Control Plans</div>
                    <div v-if="w.assignments.filter(a => a.processStatus === 'active').length === 0" class="text-xs text-surface-500 italic">No control plans assigned.</div>
                    <div v-else class="flex flex-wrap gap-1.5">
                      <span v-for="a in w.assignments.filter(a => a.processStatus === 'active')" :key="a.processId"
                        class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-surface-700 border border-surface-600 rounded-lg text-xs text-slate-300">
                        <span class="font-mono text-surface-400">{{ a.processCode }}</span>
                        <span>{{ a.processName }}</span>
                        <span class="text-surface-500">·</span>
                        <span class="font-medium">{{ a.carModelName }}</span>
                      </span>
                    </div>
                  </div>
                  <!-- Tools -->
                  <div>
                    <div class="text-[10px] font-bold text-surface-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <Wrench :size="10"/>
                      Tools
                    </div>
                    <div v-if="!workerTools[w.id]" class="text-xs text-surface-500 italic">Loading…</div>
                    <div v-else-if="workerTools[w.id].length === 0" class="text-xs text-surface-500 italic">No tools assigned.</div>
                    <div v-else class="flex flex-wrap gap-1.5">
                      <span v-for="t in workerTools[w.id]" :key="t.id"
                        :class="['inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border', toolStatusColor(t.status)]">
                        <Wrench :size="10"/>
                        <span class="font-mono font-bold">{{ t.toolId }}</span>
                        <span class="opacity-60">{{ t.typeName }}</span>
                        <span class="opacity-50">·</span>
                        <span>{{ toolStatusLabel(t.status) }}</span>
                      </span>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </AppCard>

      <!-- Pagination -->
      <VrdPagination
        :current-page="workersStore.page"
        :total-pages="totalPages"
        :total-items="workersStore.total"
        :per-page="workersStore.limit"
        :per-page-options="[20, 50, 100]"
        @update:page="onPageChange"
        @update:per-page="onPerPageChange"
      />
    </template>

    <!-- Add / Edit modal -->
    <AppModal :open="showAdd || !!editTarget"
      :title="editTarget ? `Edit — ${editTarget.name}` : 'Add Worker'"
      @close="showAdd = false; editTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Full Name">
          <AppInput v-model="form.name" placeholder="e.g. Ali Hassan" @keyup.enter="saveForm"/>
        </FormField>
        <FormField label="Worker ID">
          <AppInput v-model="form.workerId" placeholder="e.g. W-0042" @keyup.enter="saveForm"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAdd = false; editTarget = null">Cancel</AppButton>
        <AppButton :disabled="formLoading" @click="saveForm">
          {{ formLoading ? 'Saving…' : (editTarget ? 'Save Changes' : 'Add Worker') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- Delete confirm -->
    <ConfirmDialog
      :open="!!deleteTarget"
      title="Delete Worker"
      danger
      label="Delete"
      :message="`Delete worker &quot;${deleteTarget?.name}&quot;? All their control plan assignments will be removed.`"
      @close="deleteTarget = null"
      @confirm="doDelete"/>
  </div>
</template>
