<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Component } from 'vue'
import { useLinesStore } from '@/stores/lines'
import { useDashboardStore } from '@/stores/dashboard'
import { useUsersStore } from '@/stores/users'
import { ROUTES } from '@/constants/routeConstant'
import StatCard   from '@/components/ui/StatCard.vue'
import AppCard    from '@/components/ui/AppCard.vue'
import AppBadge   from '@/components/ui/AppBadge.vue'
import PageHeader   from '@/components/ui/PageHeader.vue'
import AppSkeleton  from '@/components/ui/AppSkeleton.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import {
  Factory, Cog, Car, AlertTriangle, Loader2,
  Scissors, Wrench, Settings, Building2, Flag,
  Upload, User, Package, ArrowRightLeft, FileText,
} from 'lucide-vue-next'

const router     = useRouter()
const dashboard  = useDashboardStore()
const usersStore = useUsersStore()
const linesStore = useLinesStore()

onMounted(() => dashboard.fetchStats())

const stats = computed(() => dashboard.stats)

// ─── Stat cards ───────────────────────────────────────────────────────────────
const totalStations  = computed(() => stats.value?.totalStations  ?? 0)
const totalProcesses = computed(() => stats.value?.totalProcesses ?? 0)
const activeModels   = computed(() => stats.value?.totalCarModels ?? 0)
const missingCP      = computed(() => stats.value?.missingCPCount ?? 0)

// ─── Lines — merge backend stats into lines store for icons/colors ───────────
const enrichedLines = computed(() =>
  linesStore.lines.map(line => ({
    ...line,
    ...(stats.value?.lines.find(l => l.id === line.id) ?? {
      stationCount:   0,
      processCount:   0,
      missingCPCount: 0,
    }),
  })),
)

// ─── Icon/color map ───────────────────────────────────────────────────────────
const LINE_ICONS: Record<string, Component> = {
  scissors: Scissors, wrench: Wrench, settings: Settings, building2: Building2,
  flag: Flag, car: Car, zap: Cog, box: Package, factory: Factory,
}
const auditTypeColors: Record<string, string> = {
  upload: '#6366F1', user: '#8B5CF6', station: '#10B981',
  archive: '#F59E0B', migrate: '#0EA5E9', model: '#EC4899',
}
const auditTypeIcons: Record<string, Component> = {
  upload: Upload, user: User, station: Factory,
  archive: Package, migrate: ArrowRightLeft, model: Car,
}
</script>

<template>
  <div class="p-8">
    <PageHeader title="Dashboard" subtitle="Factory overview and quick actions"/>

    <!-- Loading skeleton -->
    <template v-if="dashboard.loading && !stats">
      <div class="grid grid-cols-4 gap-4 mb-7">
        <div v-for="i in 4" :key="i" class="bg-surface-800 rounded-xl p-5 border border-surface-700 space-y-3">
          <AppSkeleton height="h-3" width="w-24"/>
          <AppSkeleton height="h-8" width="w-16"/>
          <AppSkeleton height="h-2.5" width="w-32"/>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-5">
        <div v-for="i in 2" :key="i" class="bg-surface-800 rounded-xl p-5 border border-surface-700">
          <AppSkeleton height="h-4" width="w-40" class="mb-4"/>
          <SkeletonTable :rows="5" :cols="3"/>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- Stat cards -->
      <div class="grid grid-cols-4 gap-4 mb-7">
        <StatCard label="Total Stations"    :value="totalStations"  color="#6366F1">
          <template #icon><Factory/></template>
        </StatCard>
        <StatCard label="Total Processes"   :value="totalProcesses" color="#0EA5E9">
          <template #icon><Cog/></template>
        </StatCard>
        <StatCard label="Active Car Models" :value="activeModels"   color="#10B981">
          <template #icon><Car/></template>
        </StatCard>
        <StatCard label="Missing CPs" :value="missingCP" :color="missingCP > 0 ? '#EF4444' : '#10B981'">
          <template #icon><AlertTriangle/></template>
        </StatCard>
      </div>

      <div class="grid grid-cols-2 gap-5">
        <!-- Assembly lines -->
        <AppCard>
          <h3 class="text-sm font-bold text-slate-100 mb-4">Assembly Lines</h3>
          <div
            v-for="line in enrichedLines" :key="line.id"
            @click="router.push({ name: ROUTES.assemblyLineView.name, params: { lineId: line.id } })"
            class="flex items-center gap-3 py-3 border-b border-surface-700 last:border-0 cursor-pointer hover:bg-surface-700/50 -mx-1 px-1 rounded transition-colors">
            <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                 :style="{ background: line.color + '22' }">
              <component :is="LINE_ICONS[line.icon]" :size="18" :style="{ color: line.color }"/>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-semibold text-slate-300">{{ line.name }}</div>
              <div class="text-xs text-surface-200">
                {{ line.stationCount }} stations · {{ line.processCount }} processes
                <span v-if="line.missingCPCount" class="text-red-400 ml-1">
                  · {{ line.missingCPCount }} missing CP
                </span>
              </div>
            </div>
            <AppBadge :color="line.stationCount === 0 ? '#F59E0B' : '#10B981'">
              {{ line.stationCount === 0 ? 'Upcoming' : 'Active' }}
            </AppBadge>
          </div>
        </AppCard>

        <!-- Recent activity -->
        <AppCard>
          <h3 class="text-sm font-bold text-slate-100 mb-4">Recent Activity</h3>
          <div
            v-for="log in (stats?.recentActivity ?? [])"
            :key="log.id"
            class="flex gap-3 py-2.5 border-b border-surface-700 last:border-0">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                 :style="{ background: (auditTypeColors[log.type] ?? '#6366F1') + '22' }">
              <component
                :is="auditTypeIcons[log.type] ?? FileText"
                :size="15"
                :style="{ color: auditTypeColors[log.type] ?? '#6366F1' }"/>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold text-slate-300 truncate">{{ log.action }}</div>
              <div class="text-xs text-surface-200 truncate">{{ log.target }} · {{ usersStore.users.find(u => u.id === log.performedBy)?.name ?? log.performedBy }}</div>
            </div>
            <div class="text-[10px] text-surface-400 whitespace-nowrap">
              {{ new Date(log.createdAt).toLocaleDateString() }}
            </div>
          </div>
          <div v-if="!stats?.recentActivity?.length" class="py-8 text-center text-sm text-surface-300">
            No recent activity.
          </div>
        </AppCard>
      </div>
    </template>
  </div>
</template>