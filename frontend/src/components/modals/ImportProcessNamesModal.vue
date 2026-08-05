<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import AppModal  from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'
import { Loader2, Copy } from 'lucide-vue-next'

export interface ImportProcess {
  id:         string
  name:       string
  carModelId: string
  status:     string
}

export interface CarModelOption {
  value: string
  label: string
}

const props = defineProps<{
  stationName:      string
  targetModelName:  string
  targetModelId:    string
  /** All active processes on this station across all car models */
  stationProcesses: ImportProcess[]
  /** Active car model options excluding the current target */
  sourceOptions:    CarModelOption[]
  loading:          boolean
}>()

const emit = defineEmits<{
  close:   []
  confirm: [names: string[], carModelId: string]
}>()

const sourceModelId = ref(props.sourceOptions[0]?.value ?? '')
const selectedIds   = ref<string[]>([])

// Reset selection when source changes
watch(sourceModelId, () => { selectedIds.value = [] })

const candidates = computed(() =>
  props.stationProcesses.filter(
    p => p.carModelId === sourceModelId.value && p.status === 'active',
  ),
)

const existingNames = computed(() => {
  return new Set(
    props.stationProcesses
      .filter(p => p.carModelId === props.targetModelId)
      .map(p => p.name.trim().toLowerCase()),
  )
})

const selectableIds = computed(() =>
  candidates.value
    .filter(p => !existingNames.value.has(p.name.trim().toLowerCase()))
    .map(p => p.id),
)

const allSelected = computed(
  () => selectableIds.value.length > 0 && selectedIds.value.length === selectableIds.value.length,
)
const someSelected = computed(
  () => selectedIds.value.length > 0 && !allSelected.value,
)

function toggleAll() {
  selectedIds.value = allSelected.value ? [] : [...selectableIds.value]
}

function toggle(id: string) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter(x => x !== id)
    : [...selectedIds.value, id]
}

function submit() {
  const names = candidates.value
    .filter(p => selectedIds.value.includes(p.id))
    .map(p => p.name)
  emit('confirm', names, props.targetModelId)
}

function close() {
  selectedIds.value = []
  emit('close')
}
</script>

<template>
  <AppModal :open="true" title="Import Process Names" :wide="true" @close="close">
    <p class="text-sm text-surface-200 mb-5">
      Copy process names from another car model into
      <strong class="text-slate-200">{{ targetModelName }}</strong>
      on <strong class="text-slate-200">{{ stationName }}</strong>.
      Only names will be imported — no control plans.
    </p>

    <FormField label="Copy names from" class="mb-5">
      <AppSelect v-model="sourceModelId" :options="sourceOptions"/>
    </FormField>

    <FormField label="Select processes to import">
      <div class="border border-surface-600 rounded-lg overflow-hidden">

        <!-- Select-all header -->
        <div class="flex items-center gap-3 px-4 py-2.5 bg-surface-800 border-b border-surface-600">
          <input
            type="checkbox"
            class="accent-brand-500"
            :checked="allSelected"
            :indeterminate="someSelected"
            @change="toggleAll"
          />
          <span class="text-xs font-bold text-surface-200">
            {{ candidates.length }} process(es) in source
          </span>
          <span class="ml-auto text-xs text-surface-300">{{ selectedIds.length }} selected</span>
        </div>

        <!-- Empty state -->
        <div v-if="!candidates.length" class="px-4 py-8 text-center text-sm text-surface-300">
          No active processes found for this car model on {{ stationName }}.
        </div>

        <!-- Rows -->
        <div v-else class="max-h-60 overflow-y-auto">
          <label
            v-for="p in candidates" :key="p.id"
            :class="['flex items-center gap-3 px-4 py-2.5 border-b border-surface-700 last:border-0 transition-colors',
                     existingNames.has(p.name.trim().toLowerCase())
                       ? 'opacity-50 cursor-not-allowed'
                       : selectedIds.includes(p.id) ? 'bg-brand-500/10 cursor-pointer' : 'hover:bg-surface-700 cursor-pointer']">
            <input
              type="checkbox"
              class="accent-brand-500"
              :checked="selectedIds.includes(p.id)"
              :disabled="existingNames.has(p.name.trim().toLowerCase())"
              @change="toggle(p.id)"
            />
            <span class="text-sm text-slate-300 flex-1">{{ p.name }}</span>
            <span
              v-if="existingNames.has(p.name.trim().toLowerCase())"
              class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface-600 text-surface-300">
              already exists
            </span>
          </label>
        </div>
      </div>
    </FormField>

    <div class="flex gap-3 justify-end mt-5">
      <AppButton variant="secondary" @click="close">Cancel</AppButton>
      <AppButton :disabled="!selectedIds.length || loading" @click="submit">
        <Loader2 v-if="loading" :size="14" class="animate-spin"/>
        <Copy v-else :size="14"/>
        Import {{ selectedIds.length ? `(${selectedIds.length})` : '' }}
      </AppButton>
    </div>
  </AppModal>
</template>