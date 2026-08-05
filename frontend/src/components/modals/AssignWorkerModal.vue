<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { workersService } from '@/services/workers.service'
import type { ApiWorker } from '@/services/workers.service'
import AppModal  from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import { Search, UserCheck, X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  /** IDs of the process(es) to (re)assign */
  processIds: string[]
  /** Currently assigned worker ID (if any) */
  currentWorkerId: string | null
  /** Optional title override */
  title?: string
}>()

const emit = defineEmits<{
  close: []
  assigned: [workerId: string | null]
}>()

const workers      = ref<ApiWorker[]>([])
const loading      = ref(false)
const saving       = ref(false)
const search       = ref('')
const selectedId   = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    workers.value = await workersService.listAll()
  } finally {
    loading.value = false
  }
}

watch(() => props.open, open => {
  if (open) {
    selectedId.value = props.currentWorkerId
    search.value = ''
    load()
  }
})

onMounted(() => {
  if (props.open) {
    selectedId.value = props.currentWorkerId
    load()
  }
})

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return workers.value
  return workers.value.filter(w =>
    w.name.toLowerCase().includes(q) || w.workerId.toLowerCase().includes(q),
  )
})

function select(id: string) {
  selectedId.value = selectedId.value === id ? null : id
}

async function confirm() {
  saving.value = true
  try {
    emit('assigned', selectedId.value)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal :open="open" :title="title ?? 'Assign Worker'" @close="emit('close')">
    <!-- Search -->
    <div class="relative mb-3">
      <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"/>
      <input v-model="search" placeholder="Search by name or ID…"
        class="w-full bg-surface-800 border border-surface-600 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"/>
    </div>

    <!-- Unassign option -->
    <button @click="selectedId = null"
      :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium mb-1 transition-all border',
               selectedId === null
                 ? 'bg-red-500/10 border-red-500/40 text-red-300'
                 : 'border-transparent text-surface-300 hover:bg-surface-800']">
      <X :size="14" class="flex-shrink-0"/>
      Unassigned
    </button>

    <!-- Worker list -->
    <div v-if="loading" class="py-8 text-center text-sm text-surface-400">Loading workers…</div>
    <div v-else-if="filtered.length === 0" class="py-8 text-center text-sm text-surface-400">No workers found</div>
    <div v-else class="space-y-1 max-h-72 overflow-y-auto pr-1">
      <button v-for="w in filtered" :key="w.id"
        @click="select(w.id)"
        :class="['w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all border',
                 selectedId === w.id
                   ? 'bg-brand-500/15 border-brand-500/50 text-brand-300'
                   : 'border-transparent text-slate-200 hover:bg-surface-800']">
        <div class="w-7 h-7 rounded-full bg-surface-700 flex items-center justify-center flex-shrink-0 text-xs font-bold text-surface-200">
          {{ w.name.charAt(0).toUpperCase() }}
        </div>
        <div class="flex-1 text-left min-w-0">
          <div class="font-semibold truncate">{{ w.name }}</div>
          <div class="text-[10px] text-surface-400 font-mono">{{ w.workerId }}</div>
        </div>
        <UserCheck v-if="selectedId === w.id" :size="14" class="text-brand-400 flex-shrink-0"/>
      </button>
    </div>

    <div class="flex gap-3 justify-end mt-5">
      <AppButton variant="secondary" @click="emit('close')">Cancel</AppButton>
      <AppButton :disabled="saving" @click="confirm">
        {{ saving ? 'Saving…' : (selectedId ? 'Assign Worker' : 'Unassign') }}
      </AppButton>
    </div>
  </AppModal>
</template>
