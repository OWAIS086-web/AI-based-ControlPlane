<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLinesStore } from '@/stores/lines'
import { useStationsStore } from '@/stores/stations'
import { useCarModelsStore } from '@/stores/carModels'
import { processesService } from '@/services/processes.service'
import type { ApiProcess } from '@/services/processes.service'
import AppCard   from '@/components/ui/AppCard.vue'
import AppBadge  from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import PageHeader    from '@/components/ui/PageHeader.vue'
import VrdPagination from '@/components/ui/VrdPagination.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import { Search, X } from 'lucide-vue-next'

const router     = useRouter()
const stStore    = useStationsStore()
const cmStore    = useCarModelsStore()
const linesStore = useLinesStore()

// ── Filter state ──────────────────────────────────────────────────────────────
const q  = ref('')
const fl = ref('all')
const fm = ref('all')
const fs = ref('all')

// ── Pagination state ──────────────────────────────────────────────────────────
const currentPage = ref(1)
const perPage     = ref(20)

// ── Data state ────────────────────────────────────────────────────────────────
const processes = ref<ApiProcess[]>([])
const total     = ref(0)
const loading   = ref(false)

// ── Dropdown options ──────────────────────────────────────────────────────────
const lineOptions    = computed(() => [{ value:'all', label:'All Lines' }, ...linesStore.lines.map(l => ({ value: l.id, label: l.name }))])
const modelOptions   = computed(() => [{ value:'all', label:'All Models' }, ...cmStore.activeCarModels.map(m => ({ value: m.id, label: m.name }))])
const stationOptions = computed(() => {
  if (fl.value === 'all') return [{ value:'all', label:'All Stations' }]
  return [{ value:'all', label:'All Stations' }, ...(stStore.stations[fl.value] ?? []).map(s => ({ value: s.id, label: s.name }))]
})

// ── Lookup helpers ────────────────────────────────────────────────────────────
const stationNameMap = computed(() => {
  const map: Record<string, string> = {}
  for (const stns of Object.values(stStore.stations)) {
    for (const s of stns) map[s.id] = s.name
  }
  return map
})

function lineFor(lineId: string) {
  return linesStore.lines.find(l => l.id === lineId)
}

// Enrich raw API processes with display fields from the stores
const shown = computed(() =>
  processes.value.map(p => ({
    ...p,
    hasMissingCP: p.hasMissingCp || !p.latestVersion,
    lineName:    lineFor(p.lineId)?.name  ?? p.lineId,
    lineColor:   lineFor(p.lineId)?.color ?? '#6366F1',
    stationName: stationNameMap.value[p.stationId] ?? p.stationId,
  }))
)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))

// ── Fetch ─────────────────────────────────────────────────────────────────────
async function fetchProcesses() {
  loading.value = true
  try {
    const res = await processesService.list({
      page:  currentPage.value,
      limit: perPage.value,
      ...(fl.value !== 'all' && { lineId:     fl.value }),
      ...(fs.value !== 'all' && { stationId:  fs.value }),
      ...(fm.value !== 'all' && { carModelId: fm.value }),
      ...(q.value            && { search:     q.value  }),
    })
    processes.value = res.data
    total.value     = res.meta.total
  } finally {
    loading.value = false
  }
}

// ── Watchers ──────────────────────────────────────────────────────────────────

// Debounce search so we don't fire on every keystroke
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(q, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { currentPage.value = 1; fetchProcesses() }, 300)
})

// When the line filter changes, reset the station filter then re-fetch once
// (small debounce absorbs the fl+fs changing in the same tick)
let filterTimer: ReturnType<typeof setTimeout> | null = null
function scheduleFilterFetch() {
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(() => { currentPage.value = 1; fetchProcesses() }, 30)
}

watch(fl, () => { fs.value = 'all'; scheduleFilterFetch() })
watch([fm, fs, perPage], scheduleFilterFetch)

watch(currentPage, fetchProcesses)

// ── Helpers ───────────────────────────────────────────────────────────────────
const hasFilters = computed(() => fl.value !== 'all' || fm.value !== 'all' || fs.value !== 'all' || q.value !== '')

function clearFilters() { fl.value = 'all'; fm.value = 'all'; fs.value = 'all'; q.value = '' }

function resolvedCarModel(p: ApiProcess) {
  return p.carModel ?? cmStore.carModels.find(m => m.id === p.carModelId) ?? null
}

onMounted(() => {
  cmStore.fetchCarModels()
  linesStore.lines.forEach(l => stStore.fetchStations(l.id))
  fetchProcesses()
})
</script>

<template>
  <div class="p-8">
    <PageHeader title="Process Management" :subtitle="`${total} processes`"/>

    <div class="flex gap-3 mb-5 flex-wrap">
      <div class="relative">
        <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-300"/>
        <input v-model="q" placeholder="Search processes…" class="pl-8 pr-3 py-2 bg-surface-950 border border-surface-600 rounded-lg text-sm text-slate-100 placeholder:text-surface-300 focus:outline-none focus:border-brand-500 w-52"/>
      </div>
      <AppSelect v-model="fl" :options="lineOptions" class="w-40"/>
      <AppSelect v-if="fl!=='all'" v-model="fs" :options="stationOptions" class="w-40"/>
      <AppSelect v-model="fm" :options="modelOptions" class="w-40"/>
      <AppButton v-if="hasFilters" variant="ghost" size="sm" @click="clearFilters"><X :size="14"/> Clear</AppButton>
    </div>

    <AppCard :no-pad="true">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-surface-800 border-b border-surface-600">
              <th v-for="h in ['Process','Code','Line','Station','Car Model','Versions','Latest','Status','']" :key="h"
                  class="px-4 py-3 text-left text-[10px] font-bold text-surface-300 uppercase tracking-widest whitespace-nowrap">{{ h }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9" class="p-0"><SkeletonTable :rows="8" :cols="5"/></td>
            </tr>
            <template v-else>
              <tr v-for="(p, i) in shown" :key="p.id"
                  :class="['border-b border-surface-700/50 hover:bg-surface-800/50 transition-colors', i%2===0?'':'bg-surface-950/30']">
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <span v-if="p.hasMissingCP" class="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0"/>
                    <span class="font-semibold text-slate-300">{{ p.name }}</span>
                  </div>
                </td>
                <td class="px-4 py-3"><code class="text-xs text-surface-300 font-mono">{{ p.code }}</code></td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: p.lineColor }"/>
                    <span class="text-xs text-surface-200">{{ p.lineName }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-xs text-surface-200">{{ p.stationName }}</td>
                <td class="px-4 py-3"><AppBadge :color="resolvedCarModel(p)?.color || '#6366F1'">{{ resolvedCarModel(p)?.name }}</AppBadge></td>
                <td class="px-4 py-3 text-xs text-surface-200">{{ p.versionCount }}</td>
                <td class="px-4 py-3">
                  <span v-if="p.latestVersion" class="text-xs font-mono" :style="{ color: p.lineColor }">{{ p.latestVersion.version }}</span>
                  <span v-else class="text-xs text-red-400">None</span>
                </td>
                <td class="px-4 py-3"><AppBadge :color="p.status==='active'?'#10B981':'#475569'">{{ p.status }}</AppBadge></td>
                <td class="px-4 py-3"><AppButton size="sm" @click="router.push({ name: 'process-detail', params: { lineId: p.lineId, processId: p.id }, query: { car: resolvedCarModel(p)?.name || undefined } })">View</AppButton></td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!loading && !shown.length" class="text-center py-10 text-surface-300 text-sm">No processes match your filters.</div>
        <div v-if="total > 0" class="px-4 py-3 border-t border-surface-700">
          <VrdPagination
            :current-page="currentPage"
            :total-pages="totalPages"
            :total-items="total"
            :per-page="perPage"
            @update:page="currentPage = $event"
            @update:per-page="perPage = $event"
          />
        </div>
      </div>
    </AppCard>
  </div>
</template>
