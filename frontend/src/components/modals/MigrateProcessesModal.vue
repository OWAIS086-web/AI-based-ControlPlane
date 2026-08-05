<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useCarModelsStore } from '@/stores/carModels'
import { useConfigStore } from '@/stores/config'
import AppModal  from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppBadge  from '@/components/ui/AppBadge.vue'
import FormField from '@/components/ui/FormField.vue'
import { ArrowRightLeft, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  targetStationName: string
  targetStationId: string
}>()

const emit = defineEmits<{
  close:   []
  confirm: [fromLine: string, fromStation: string, processIds: string[]]
}>()

const stStore      = useStationsStore()
const carStore     = useCarModelsStore()
const linesStore   = useLinesStore()
const configStore  = useConfigStore()

function processLabel(p: { name: string; latestVersion?: { fileName?: string | null } | null }) {
  if (configStore.cardDisplayMode === 'filename') return p.latestVersion?.fileName ?? p.name
  return p.name
}

const fromLine      = ref(linesStore.lines[0]?.id ?? '')
const fromStation   = ref('')
const selected      = ref<string[]>([])
const loadingStations = ref(false)
const carFilter     = ref('')

const fromStations   = computed(() => stStore.stations[fromLine.value] ?? [])
const fromStationData = computed(() => fromStations.value.find(s => s.id === fromStation.value))

function resolveCarModel(carModelId: string) {
  return carStore.carModels.find(m => m.id === carModelId) ?? null
}

const activeProcesses = computed(() =>
  fromStationData.value?.processes.filter(p => p.status === 'active') ?? [],
)

const carOptions = computed(() => {
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const p of activeProcesses.value) {
    const car = resolveCarModel(p.carModelId)
    if (car && !seen.has(car.id)) {
      seen.add(car.id)
      opts.push({ value: car.id, label: `${car.name} (${car.code})` })
    }
  }
  return opts
})

const filteredProcesses = computed(() =>
  carFilter.value
    ? activeProcesses.value.filter(p => p.carModelId === carFilter.value)
    : activeProcesses.value,
)

const lineOptions = computed(() =>
  linesStore.lines.map(l => ({ value: l.id, label: l.name })),
)
const stationOptions = computed(() =>
  fromStations.value
    .filter(s => s.id !== props.targetStationId)
    .map(s => ({ value: s.id, label: s.name })),
)

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
  fromStation.value = ''
  selected.value = []
  await loadLineStations(fromLine.value)
}
function onStationChange() { selected.value = []; carFilter.value = '' }

onMounted(() => {
  loadLineStations(fromLine.value)
  if (!carStore.carModels.length) carStore.fetchCarModels()
})

function toggle(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter(x => x !== id)
    : [...selected.value, id]
}

function submit() {
  emit('confirm', fromLine.value, fromStation.value, selected.value)
  selected.value = []
}

function close() {
  selected.value = []
  emit('close')
}
</script>

<template>
  <AppModal :open="true" title="Migrate Control Plans" :wide="true" @close="close">
    <p class="text-sm text-surface-200 mb-5">
      Migrate individual processes to
      <strong class="text-slate-200">{{ targetStationName }}</strong>.
    </p>

    <div class="grid grid-cols-2 gap-4 mb-5">
      <FormField label="Source Line">
        <AppSelect v-model="fromLine" :options="lineOptions" @update:modelValue="onLineChange"/>
      </FormField>
      <FormField label="Source Station">
        <div class="flex items-center gap-2">
          <AppSelect v-model="fromStation" :options="stationOptions" :placeholder="loadingStations ? 'Loading…' : 'Select station…'" :disabled="loadingStations" class="flex-1" @update:modelValue="onStationChange"/>
          <Loader2 v-if="loadingStations" :size="16" class="text-surface-400 animate-spin shrink-0"/>
        </div>
      </FormField>
    </div>

    <template v-if="fromStationData">
      <div v-if="carOptions.length > 1" class="mb-4">
        <FormField label="Filter by Car Model">
          <div class="flex items-center gap-2">
            <AppSelect v-model="carFilter" :options="carOptions" placeholder="All cars" class="flex-1"/>
            <button v-if="carFilter" type="button" @click="carFilter = ''"
              class="text-surface-300 hover:text-slate-100 transition-colors text-lg leading-none">×</button>
          </div>
        </FormField>
      </div>

      <FormField label="Select Processes to Migrate">
        <div class="border border-surface-600 rounded-lg max-h-52 overflow-y-auto">
          <div v-if="!filteredProcesses.length" class="px-4 py-3 text-sm text-surface-300 text-center">
            No active processes{{ carFilter ? ' for this car model' : '' }}.
          </div>
          <label
            v-for="p in filteredProcesses"
            :key="p.id"
            :class="['flex items-center gap-3 px-4 py-2.5 border-b border-surface-700 last:border-0 cursor-pointer transition-colors',
                     selected.includes(p.id) ? 'bg-brand-500/10' : 'hover:bg-surface-700']">
            <input type="checkbox" :checked="selected.includes(p.id)" @change="toggle(p.id)" class="accent-brand-500"/>
            <span class="text-sm text-slate-300 flex-1">{{ processLabel(p) }}</span>
            <template v-for="car in [resolveCarModel(p.carModelId)]" :key="0">
              <AppBadge v-if="car" :color="car.color">{{ car.name }}</AppBadge>
            </template>
            <span class="text-[10px] font-mono text-surface-300">{{ p.code }} · {{ p.versionCount }}v</span>
          </label>
        </div>
      </FormField>

      <div class="flex gap-3 justify-end mt-5 items-center">
        <span class="text-sm text-surface-200">{{ selected.length }} selected</span>
        <AppButton variant="secondary" @click="close">Cancel</AppButton>
        <AppButton :disabled="!selected.length || !fromStation" @click="submit">
          <ArrowRightLeft :size="14"/>
          Migrate {{ selected.length ? `(${selected.length})` : '' }}
        </AppButton>
      </div>
    </template>
  </AppModal>
</template>