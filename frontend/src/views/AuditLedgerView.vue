<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import type { Component } from 'vue'
import { useAuditStore } from '@/stores/audit'
import AppCard    from '@/components/ui/AppCard.vue'
import AppBadge   from '@/components/ui/AppBadge.vue'
import PageHeader     from '@/components/ui/PageHeader.vue'
import VrdPagination from '@/components/ui/VrdPagination.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import { Search, Upload, User, Factory, Package, ArrowRightLeft, Car, FileText, Wrench, HardHat, AlertTriangle } from 'lucide-vue-next'

const auditStore = useAuditStore()

const TYPE_COLOR: Record<string, string> = {
  upload: '#6366F1', user: '#8B5CF6',    station: '#10B981',
  archive: '#F59E0B', migrate: '#0EA5E9', model: '#EC4899',
  tool: '#F97316',   worker: '#06B6D4',  tool_request: '#EF4444',
}
const TYPE_ICONS: Record<string, Component> = {
  upload: Upload, user: User,  station: Factory,
  archive: Package, migrate: ArrowRightLeft, model: Car,
  tool: Wrench, worker: HardHat, tool_request: AlertTriangle,
}
const types = ['all', ...Object.keys(TYPE_COLOR)]

const ft      = ref('all')
const q       = ref('')
const page    = ref(1)
const perPage = ref(25)

function fetch() {
  auditStore.fetchAuditLog({
    page:   page.value,
    limit:  perPage.value,
    type:   ft.value !== 'all' ? ft.value as any : undefined,
    search: q.value || undefined,
  })
}

const loading = ref(true)
onMounted(async () => {
  try { await Promise.all([fetch(), auditStore.fetchTypeCounts()]) } finally { loading.value = false }
})

watch([ft, q], () => {
  page.value = 1
  fetch()
})

watch([page, perPage], fetch)
</script>

<template>
  <div class="p-8">
    <PageHeader title="Audit Ledger" subtitle="Immutable record of all system actions"/>

    <!-- Stats grid -->
    <div class="grid grid-cols-6 gap-3 mb-7">
      <AppCard v-for="([type, color]) in Object.entries(TYPE_COLOR)" :key="type" class="!p-4">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center mb-2" :style="{ background: color + '22' }">
          <component :is="TYPE_ICONS[type] || FileText" :size="15" :style="{ color }" />
        </div>
        <div class="text-2xl font-black font-mono" :style="{ color }">{{ auditStore.typeCounts[type] ?? '—' }}</div>
        <div class="text-xs text-surface-300 capitalize mt-0.5">{{ type }}s</div>
      </AppCard>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 mb-5 flex-wrap items-center">
      <div class="relative">
        <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-300"/>
        <input v-model="q" placeholder="Search logs…"
          class="pl-8 pr-3 py-2 bg-surface-950 border border-surface-600 rounded-lg text-sm text-slate-100 placeholder:text-surface-300 focus:outline-none focus:border-brand-500 w-56"/>
      </div>
      <div class="flex gap-1.5 flex-wrap">
        <button v-for="t in types" :key="t" @click="ft = t"
          :class="['px-3 py-1.5 rounded-full text-xs font-bold transition-all capitalize border flex items-center gap-1',
                   ft === t ? 'text-white border-transparent' : 'bg-surface-800 text-surface-200 border-surface-600 hover:bg-surface-700']"
          :style="ft === t ? { background: TYPE_COLOR[t] || '#6366F1' } : {}">
          <component v-if="t !== 'all'" :is="TYPE_ICONS[t] || FileText" :size="11" />
          {{ t === 'all' ? 'All' : t }}
        </button>
      </div>
    </div>

    <!-- Log list -->
    <AppCard :no-pad="true">
      <SkeletonTable v-if="loading" :rows="10" :cols="3"/>
      <div v-else v-for="(log, i) in auditStore.auditLog" :key="`${log.id}-${i}`"
           :class="['flex items-center gap-4 px-5 py-3.5 border-b border-surface-700/60 last:border-0', i%2===0?'':'bg-surface-950/40']">
        <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
             :style="{ background: (TYPE_COLOR[log.type] || '#475569') + '20' }">
          <component :is="TYPE_ICONS[log.type] || FileText" :size="15" :style="{ color: TYPE_COLOR[log.type] || '#475569' }" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-bold text-slate-300">{{ log.action }}</div>
          <div class="text-xs text-surface-300 truncate">{{ log.target }}</div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-semibold text-surface-200">{{ log.user }}</div>
          <div class="text-[10px] text-surface-400">{{ new Date(log.timestamp).toLocaleString() }}</div>
        </div>
        <div class="w-2 h-2 rounded-full flex-shrink-0" :style="{ background: TYPE_COLOR[log.type] || '#475569' }"/>
      </div>
      <div v-if="!auditStore.auditLog.length" class="text-center py-10 text-surface-300 text-sm">No matching log entries.</div>

      <!-- Pagination -->
      <div class="px-5 py-3 border-t border-surface-700/60">
        <VrdPagination
          :current-page="auditStore.meta.page"
          :total-pages="auditStore.meta.totalPages"
          :total-items="auditStore.meta.total"
          :per-page="perPage"
          :per-page-options="[10, 25, 50, 100]"
          @update:page="page = $event"
          @update:per-page="perPage = $event"
        />
      </div>
    </AppCard>
  </div>
</template>
