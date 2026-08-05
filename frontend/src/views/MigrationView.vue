<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useMigrationsStore } from '@/stores/migrations'
import { useCarModelsStore } from '@/stores/carModels'
import { useToast } from '@/composables/useToast'
import AppCard       from '@/components/ui/AppCard.vue'
import AppBadge      from '@/components/ui/AppBadge.vue'
import AppButton     from '@/components/ui/AppButton.vue'
import AppSelect     from '@/components/ui/AppSelect.vue'
import FormField     from '@/components/ui/FormField.vue'
import PageHeader    from '@/components/ui/PageHeader.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import VrdPagination from '@/components/ui/VrdPagination.vue'
import { ArrowRightLeft, LogOut, LogIn, RefreshCw } from 'lucide-vue-next'

const stStore    = useStationsStore()
const migStore   = useMigrationsStore()
const carStore   = useCarModelsStore()
const linesStore = useLinesStore()
const { toast }  = useToast()

const fromLine  = ref('');  const fromStn = ref('')
const toLine    = ref('');  const toStn   = ref('')
const sel       = ref<string[]>([])
const carFilter = ref('')

const page    = ref(1)
const perPage = ref(20)

const linesWithStations = computed(() =>
  linesStore.lines.filter(l => (stStore.stations[l.id] ?? []).length > 0).map(l => ({ value: l.id, label: l.name })),
)
const fromStnOpts = computed(() => (stStore.stations[fromLine.value] ?? []).map(s => ({ value: s.id, label: s.name })))
const toStnOpts   = computed(() => (stStore.stations[toLine.value] ?? []).map(s => ({ value: s.id, label: s.name })))
const fromData    = computed(() => (stStore.stations[fromLine.value] ?? []).find(s => s.id === fromStn.value))
const toData      = computed(() => (stStore.stations[toLine.value] ?? []).find(s => s.id === toStn.value))

function resolveCarModel(carModelId: string) {
  return carStore.carModels.find(m => m.id === carModelId) ?? null
}

const activeProcesses = computed(() => fromData.value?.processes.filter(p => p.status === 'active') ?? [])

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

function fetchHistory() {
  migStore.fetchMigrations({ page: page.value, limit: perPage.value })
}

const loading = ref(true)
onMounted(async () => {
  try {
    await Promise.all(linesStore.lines.map(l => stStore.fetchStations(l.id)))
    fromLine.value = linesStore.lines[0]?.id ?? ''
    toLine.value   = linesStore.lines[1]?.id ?? linesStore.lines[0]?.id ?? ''
    await fetchHistory()
  } finally { loading.value = false }
})

watch([page, perPage], fetchHistory)

function toggleSel(id: string) { sel.value = sel.value.includes(id) ? sel.value.filter(x => x !== id) : [...sel.value, id] }
function selectAll() { sel.value = filteredProcesses.value.map(p => p.id) }

async function doMigrate() {
  if (!fromStn.value || !toStn.value || !sel.value.length) { toast('Select source, destination, and processes', 'error'); return }
  if (fromStn.value === toStn.value) { toast('Source and destination must differ', 'error'); return }
  try {
    await migStore.migrateProcesses(fromLine.value, fromStn.value, toLine.value, toStn.value, sel.value)
    toast(`Migrated ${sel.value.length} process(es)!`)
    sel.value = []
    page.value = 1
    fetchHistory()
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}
</script>

<template>
  <div class="p-8">
    <PageHeader title="CP Migration" subtitle="Move individual control plans between stations with full audit trail"/>

    <div class="grid grid-cols-2 gap-5 mb-5">
      <AppCard>
        <div class="flex items-center gap-2 mb-4">
          <div class="w-7 h-7 rounded-lg bg-brand-500/15 flex items-center justify-center">
            <LogOut :size="14" class="text-brand-400" />
          </div>
          <h3 class="text-sm font-bold text-slate-100">Source</h3>
        </div>
        <div class="space-y-3">
          <FormField label="Line">
            <AppSelect v-model="fromLine" :options="linesWithStations" @update:modelValue="fromStn='';sel=[];carFilter=''"/>
          </FormField>
          <FormField label="Station">
            <AppSelect v-model="fromStn" :options="fromStnOpts" placeholder="Select station…" @update:modelValue="sel=[];carFilter=''"/>
          </FormField>
        </div>
      </AppCard>
      <AppCard>
        <div class="flex items-center gap-2 mb-4">
          <div class="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center">
            <LogIn :size="14" class="text-emerald-400" />
          </div>
          <h3 class="text-sm font-bold text-slate-100">Destination</h3>
        </div>
        <div class="space-y-3">
          <FormField label="Line">
            <AppSelect v-model="toLine" :options="linesWithStations" @update:modelValue="toStn=''"/>
          </FormField>
          <FormField label="Station">
            <AppSelect v-model="toStn" :options="toStnOpts" placeholder="Select station…"/>
          </FormField>
        </div>
      </AppCard>
    </div>

    <AppCard v-if="fromData" class="mb-5">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h3 class="text-sm font-bold text-slate-100">Select Individual Processes</h3>
          <p class="text-xs text-surface-200 mt-0.5">All versions and CP history will be copied to the destination.</p>
        </div>
        <div class="flex gap-2">
          <AppButton size="sm" variant="secondary" @click="selectAll">Select All</AppButton>
          <AppButton size="sm" variant="secondary" @click="sel=[]">Clear</AppButton>
        </div>
      </div>
      <div v-if="carOptions.length > 1" class="mb-4">
        <FormField label="Filter by Car Model">
          <div class="flex items-center gap-2">
            <AppSelect v-model="carFilter" :options="carOptions" placeholder="All cars" class="flex-1"/>
            <button v-if="carFilter" type="button" @click="carFilter = ''"
              class="text-surface-300 hover:text-slate-100 transition-colors text-lg leading-none">×</button>
          </div>
        </FormField>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5 mb-5">
        <label v-for="p in filteredProcesses" :key="p.id"
               :class="['flex items-start gap-2.5 p-3 rounded-lg cursor-pointer transition-all border',
                        sel.includes(p.id) ? 'bg-brand-500/10 border-brand-500' : 'bg-surface-950 border-surface-600 hover:border-surface-500']">
          <input type="checkbox" :checked="sel.includes(p.id)" @change="toggleSel(p.id)" class="accent-brand-500 mt-0.5 flex-shrink-0"/>
          <div>
            <div class="text-xs font-bold text-slate-300">{{ p.name }}</div>
            <div class="text-[10px] font-mono text-surface-300 mt-0.5">{{ p.code }}</div>
            <template v-for="car in [resolveCarModel(p.carModelId)]" :key="0">
              <AppBadge v-if="car" :color="car.color" class="mt-1.5">{{ car.name }}</AppBadge>
            </template>
            <div class="flex gap-2 mt-1.5">
              <span class="text-[10px] text-surface-300">{{ p.versionCount }}v</span>
              <span v-if="p.latestVersion" class="text-[10px] text-brand-400 font-mono">{{ p.latestVersion.version }}</span>
              <span v-if="p.hasMissingCP" class="text-[10px] text-red-400 font-bold">NO CP</span>
            </div>
          </div>
        </label>
      </div>

      <div v-if="sel.length && toStn" class="p-3 bg-sky-500/10 border border-sky-500/25 rounded-xl mb-4">
        <div class="text-xs font-bold text-sky-300 mb-1">Migration Preview</div>
        <div class="text-xs text-slate-300 mb-2">
          Moving <strong>{{ sel.length }} process{{ sel.length!==1?'es':'' }}</strong> from
          <strong>{{ fromData.name }}</strong> → <strong>{{ toData?.name || '?' }}</strong>
        </div>
        <div class="flex gap-1.5 flex-wrap">
          <span v-for="p in fromData.processes.filter(p=>sel.includes(p.id))" :key="p.id"
                class="text-[10px] bg-sky-500/15 text-sky-300 border border-sky-500/25 rounded px-2 py-0.5">{{ p.name }}</span>
        </div>
      </div>

      <div class="flex justify-end gap-3 items-center">
        <span class="text-sm text-surface-200">{{ sel.length }} selected</span>
        <AppButton :disabled="!sel.length || !toStn" @click="doMigrate">
          <ArrowRightLeft :size="15"/> Execute Migration
        </AppButton>
      </div>
    </AppCard>

    <!-- History -->
    <AppCard :no-pad="true">
      <div class="px-5 py-4 border-b border-surface-700">
        <h3 class="text-sm font-bold text-slate-100">Migration History</h3>
      </div>
      <SkeletonTable v-if="loading" :rows="5" :cols="3"/>
      <div v-else v-for="(h, i) in migStore.migrationHistory" :key="h.id"
           :class="['flex gap-4 px-5 py-4', i%2===0?'':'bg-surface-950/40', i<migStore.migrationHistory.length-1?'border-b border-surface-700':'']">
        <div class="w-9 h-9 rounded-lg bg-sky-500/15 flex items-center justify-center flex-shrink-0">
          <RefreshCw :size="16" class="text-sky-400" />
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1.5">
            <span class="text-xs font-bold text-slate-300 font-mono">{{ h.from }}</span>
            <span class="text-surface-400 text-xs">→</span>
            <span class="text-xs font-bold text-sky-400 font-mono">{{ h.to }}</span>
          </div>
          <div class="flex gap-1.5 flex-wrap">
            <span v-for="name in h.procs" :key="name"
                  class="text-[10px] bg-surface-800 text-surface-200 border border-surface-600 rounded px-1.5 py-0.5">{{ name }}</span>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs text-surface-200">{{ h.by }}</div>
          <div class="text-[10px] text-surface-300">{{ h.date }}</div>
          <AppBadge color="#10B981" class="mt-1">{{ h.status }}</AppBadge>
        </div>
      </div>
      <div v-if="!migStore.migrationHistory.length" class="text-center py-8 text-surface-300 text-sm">No migrations yet.</div>

      <!-- Pagination -->
      <div class="px-5 py-3 border-t border-surface-700">
        <VrdPagination
          :current-page="migStore.meta.page"
          :total-pages="migStore.meta.totalPages"
          :total-items="migStore.meta.total"
          :per-page="perPage"
          :per-page-options="[10, 20, 50, 100]"
          @update:page="page = $event"
          @update:per-page="perPage = $event"
        />
      </div>
    </AppCard>
  </div>
</template>
