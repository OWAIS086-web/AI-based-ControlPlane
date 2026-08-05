<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useCarModelsStore } from '@/stores/carModels'
import { useConfigStore } from '@/stores/config'
import AppModal  from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'
import { Download, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  targetStationName: string
  targetModelName:   string
  targetModelId:     string
  /** Active processes already on the target station (all car models) */
  targetProcesses:   { name: string; carModelId: string }[]
  loading:           boolean
}>()

const emit = defineEmits<{
  close:   []
  confirm: [processIds: string[]]
}>()

const stStore     = useStationsStore()
const cmStore     = useCarModelsStore()
const linesStore  = useLinesStore()
const configStore = useConfigStore()

function processLabel(p: { name: string; latestVersion?: { fileName?: string | null } | null }) {
  if (configStore.cardDisplayMode === 'filename') return p.latestVersion?.fileName ?? p.name
  return p.name
}

const fromLine      = ref(linesStore.lines[0]?.id ?? '')
const fromStation   = ref('')
const fromCarModel  = ref('')
const selected      = ref<string[]>([])
const loadingStations = ref(false)

const fromStations    = computed(() => stStore.stations[fromLine.value] ?? [])
const fromStationData = computed(() => fromStations.value.find(s => s.id === fromStation.value))

const lineOptions = computed(() => linesStore.lines.map(l => ({ value: l.id, label: l.name })))
const stationOptions = computed(() => fromStations.value.map(s => ({ value: s.id, label: s.name })))

const carModelOptions = computed(() => {
  if (!fromStationData.value) return []
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const p of fromStationData.value.processes) {
    if (p.status === 'active' && !seen.has(p.carModelId)) {
      seen.add(p.carModelId)
      const name = cmStore.carModels.find(m => m.id === p.carModelId)?.name ?? p.carModel?.name ?? p.carModelId
      opts.push({ value: p.carModelId, label: name })
    }
  }
  return opts
})

watch(carModelOptions, opts => {
  if (!opts.find(o => o.value === fromCarModel.value)) {
    fromCarModel.value = opts[0]?.value ?? ''
  }
})

const candidates = computed(() => {
  if (!fromStationData.value || !fromCarModel.value) return []
  return fromStationData.value.processes.filter(
    p => p.carModelId === fromCarModel.value && p.status === 'active',
  )
})

const existingNames = computed(() =>
  new Set(
    props.targetProcesses
      .filter(p => p.carModelId === props.targetModelId)
      .map(p => p.name.trim().toLowerCase()),
  ),
)

const selectableIds = computed(() =>
  candidates.value
    .filter(p => !existingNames.value.has(p.name.trim().toLowerCase()))
    .map(p => p.id),
)

const allSelected  = computed(() => selectableIds.value.length > 0 && selected.value.length === selectableIds.value.length)
const someSelected = computed(() => selected.value.length > 0 && !allSelected.value)

function toggleAll() {
  selected.value = allSelected.value ? [] : [...selectableIds.value]
}
function toggle(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter(x => x !== id)
    : [...selected.value, id]
}

async function loadLineStations(lineId: string) {
  if (stStore.loadedLines.has(lineId)) return
  loadingStations.value = true
  try {
    await stStore.fetchStations(lineId)
  } finally {
    loadingStations.value = false
  }
}

async function onLineChange() {
  fromStation.value  = ''
  fromCarModel.value = ''
  selected.value     = []
  await loadLineStations(fromLine.value)
}

function onStationChange() {
  fromCarModel.value = ''
  selected.value     = []
}

watch(fromCarModel, () => { selected.value = [] })

onMounted(() => loadLineStations(fromLine.value))

function submit() {
  emit('confirm', [...selected.value])
  selected.value = []
}

function close() {
  selected.value = []
  emit('close')
}
</script>

<template>
  <AppModal :open="true" title="Import Processes" :wide="true" @close="close">
    <p class="text-sm text-surface-200 mb-5">
      Copy processes (including full version history) into
      <strong class="text-slate-200">{{ targetModelName }}</strong>
      on <strong class="text-slate-200">{{ targetStationName }}</strong>.
      Processes with matching names are skipped.
    </p>

    <div class="grid grid-cols-2 gap-4 mb-4">
      <FormField label="Source Line">
        <AppSelect v-model="fromLine" :options="lineOptions" @update:modelValue="onLineChange"/>
      </FormField>
      <FormField label="Source Station">
        <div class="flex items-center gap-2">
          <AppSelect
            v-model="fromStation"
            :options="stationOptions"
            :placeholder="loadingStations ? 'Loading…' : 'Select station…'"
            :disabled="loadingStations"
            class="flex-1"
            @update:modelValue="onStationChange"
          />
          <Loader2 v-if="loadingStations" :size="16" class="text-surface-400 animate-spin shrink-0"/>
        </div>
      </FormField>
    </div>

    <template v-if="fromStation && carModelOptions.length">
      <FormField label="Source Car Model" class="mb-4">
        <AppSelect v-model="fromCarModel" :options="carModelOptions"/>
      </FormField>
    </template>

    <template v-if="fromCarModel">
      <FormField label="Select Processes to Import">
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
            <span class="ml-auto text-xs text-surface-300">{{ selected.length }} selected</span>
          </div>

          <!-- Empty state -->
          <div v-if="!candidates.length" class="px-4 py-8 text-center text-sm text-surface-300">
            No active processes found for this car model on the selected station.
          </div>

          <!-- Rows -->
          <div v-else class="max-h-60 overflow-y-auto">
            <label
              v-for="p in candidates" :key="p.id"
              :class="['flex items-center gap-3 px-4 py-2.5 border-b border-surface-700 last:border-0 transition-colors',
                       existingNames.has(p.name.trim().toLowerCase())
                         ? 'opacity-50 cursor-not-allowed'
                         : selected.includes(p.id) ? 'bg-brand-500/10 cursor-pointer' : 'hover:bg-surface-700 cursor-pointer']">
              <input
                type="checkbox"
                class="accent-brand-500"
                :checked="selected.includes(p.id)"
                :disabled="existingNames.has(p.name.trim().toLowerCase())"
                @change="toggle(p.id)"
              />
              <span class="text-sm text-slate-300 flex-1">{{ processLabel(p) }}</span>
              <span class="text-[10px] font-mono text-surface-400">{{ p.code }} · {{ p.versionCount }}v</span>
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
        <AppButton :disabled="!selected.length || loading" @click="submit">
          <Loader2 v-if="loading" :size="14" class="animate-spin"/>
          <Download v-else :size="14"/>
          Import {{ selected.length ? `(${selected.length})` : '' }}
        </AppButton>
      </div>
    </template>

    <template v-else-if="!fromStation">
      <div class="flex gap-3 justify-end mt-2">
        <AppButton variant="secondary" @click="close">Cancel</AppButton>
      </div>
    </template>
  </AppModal>
</template>
