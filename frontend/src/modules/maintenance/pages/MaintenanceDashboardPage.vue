<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import { usePaintDashboard } from '@/modules/paint-inspection/composables/usePaintDashboard'
import { useMaintenanceAuthStore } from '@/stores/maintenanceAuth'
import type { FaultRecord } from '@/services/maintenanceApi'
import type { InspectionDefect } from '@/types/paint-inspection'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const router = useRouter()
const auth   = useMaintenanceAuthStore()

const { loading, inspections, fetchDashboardData } = usePaintDashboard()

// ── Adapters ─────────────────────────────────────────────────────────
function defectSeverity(name: string): FaultRecord['severity'] {
  const n = name.toLowerCase()
  if (n.includes('crater'))                                                   return 'critical'
  if (n.includes('dent') || n.includes('glass') || n.includes('less paint')) return 'high'
  if (n.includes('major') || n.includes('black') || n.includes('sag') || n.includes('orange')) return 'medium'
  return 'low'
}

function defectStatus(d: InspectionDefect): FaultRecord['status'] {
  if ((d.repair_qty ?? 0) > 0) return 'resolved'
  if ((d.let_go_qty ?? 0) > 0) return 'open'
  return 'in_progress'
}

const allFaults = computed<FaultRecord[]>(() =>
  inspections.value.flatMap(insp =>
    insp.defects.map((d, i): FaultRecord => ({
      id:           `${insp.id}-${i}`,
      title:        d.name,
      description:  d.remarks ?? '',
      location:     insp.vehicle_parts.find(p => p.annotation?.trim())?.part_name ?? null,
      severity:     defectSeverity(d.name),
      status:       defectStatus(d),
      reportedBy:   insp.created_by_id,
      reporterName: insp.checked_by ?? insp.created_by_id,
      assignedTo:   null,
      assigneeName: null,
      resolvedAt:   null,
      createdAt:    insp.created_at,
      updatedAt:    insp.updated_at,
    }))
  )
)

// ── KPIs ─────────────────────────────────────────────────────────────
const total      = computed(() => allFaults.value.length)
const openCount  = computed(() => allFaults.value.filter(f => f.status === 'open').length)
const inProgress = computed(() => allFaults.value.filter(f => f.status === 'in_progress').length)
const resolved   = computed(() => allFaults.value.filter(f => f.status === 'resolved').length)
const critical   = computed(() => allFaults.value.filter(f => f.severity === 'critical').length)
const resolutionRate = computed(() =>
  total.value ? Math.round((resolved.value / total.value) * 100) : 0
)

// Recent unresolved defects (newest inspections first)
const recentFaults = computed<(FaultRecord & { inspectionId: number })[]>(() =>
  inspections.value
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .flatMap(insp =>
      insp.defects
        .filter(d => defectStatus(d) !== 'resolved')
        .map((d, i): FaultRecord & { inspectionId: number } => ({
          id:           `${insp.id}-${i}`,
          title:        d.name,
          description:  d.remarks ?? '',
          location:     insp.vehicle_parts.find(p => p.annotation?.trim())?.part_name ?? null,
          severity:     defectSeverity(d.name),
          status:       defectStatus(d),
          reportedBy:   insp.created_by_id,
          reporterName: insp.checked_by ?? insp.created_by_id,
          assignedTo:   null,
          assigneeName: null,
          resolvedAt:   null,
          createdAt:    insp.created_at,
          updatedAt:    insp.updated_at,
          inspectionId: insp.id,
        }))
    )
    .slice(0, 8)
)

// ── Charts ────────────────────────────────────────────────────────────
const statusChartData = computed(() => ({
  labels: ['Let Go', 'Pending', 'Repaired'],
  datasets: [{
    data: [openCount.value, inProgress.value, resolved.value],
    backgroundColor: ['#ef4444cc', '#f59e0bcc', '#10b981cc'],
    borderColor:     ['#ef4444',   '#f59e0b',   '#10b981'],
    borderWidth: 2,
  }],
}))

const trendChartData = computed(() => {
  const byWeek: Record<string, number> = {}
  inspections.value.forEach(insp => {
    const d   = new Date(insp.inspection_date)
    const day  = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    const mon  = new Date(new Date(insp.inspection_date).setDate(diff))
    const key  = mon.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    byWeek[key] = (byWeek[key] ?? 0) + (insp.defects.length || 1)
  })
  const sorted = Object.entries(byWeek).slice(-12)
  return {
    labels: sorted.map(([k]) => k),
    datasets: [{
      label: 'Defects reported',
      data: sorted.map(([, v]) => v),
      borderColor: '#f59e0b',
      backgroundColor: '#f59e0b1a',
      fill: true,
      tension: 0.4,
      pointBackgroundColor: '#f59e0b',
      pointRadius: 4,
    }],
  }
})

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: '#374151', font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: '#6b7280' }, grid: { color: '#f3f4f6' } },
    y: { ticks: { color: '#6b7280' }, grid: { color: '#f3f4f6' }, beginAtZero: true },
  },
}
const CHART_OPTS_PIE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' as const, labels: { color: '#374151', font: { size: 11 } } } },
}

const SEVERITY_COLOR: Record<string, string> = {
  low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444',
}
const STATUS_COLOR: Record<string, string> = {
  open: '#ef4444', in_progress: '#f59e0b', resolved: '#10b981',
}
const STATUS_LABEL: Record<string, string> = {
  open: 'Let Go', in_progress: 'Pending', resolved: 'Repaired',
}

function statusBg(s: string) {
  return { open: '#fef2f2', in_progress: '#fffbeb', resolved: '#f0fdf4' }[s] ?? '#f9fafb'
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="m-dashboard">

    <!-- Page header -->
    <div class="m-page-header">
      <div class="m-page-header-text">
        <h1>Maintenance Dashboard</h1>
        <p>Welcome back, {{ auth.currentUser?.name }}</p>
      </div>
      <button class="m-btn m-btn-primary" @click="router.push({ name: 'paint-inspection-new' })">
        <i class="fa-solid fa-plus"></i> New Inspection
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="m-loading">
      <i class="fa-solid fa-spinner fa-spin"></i> Loading dashboard…
    </div>

    <template v-else>

      <!-- Stat cards -->
      <div class="m-stat-grid">

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#ef4444;"></div>
          <div class="m-stat-icon" style="background:#fef2f2;color:#ef4444">
            <i class="fa-solid fa-triangle-exclamation"></i>
          </div>
          <div class="m-stat-value">{{ openCount }}</div>
          <div class="m-stat-label">Let Go</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#f59e0b;"></div>
          <div class="m-stat-icon" style="background:#fffbeb;color:#d97706">
            <i class="fa-solid fa-clock"></i>
          </div>
          <div class="m-stat-value">{{ inProgress }}</div>
          <div class="m-stat-label">Pending</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#10b981;"></div>
          <div class="m-stat-icon" style="background:#f0fdf4;color:#059669">
            <i class="fa-solid fa-circle-check"></i>
          </div>
          <div class="m-stat-value">{{ resolved }}</div>
          <div class="m-stat-label">Repaired</div>
        </div>

        <div class="m-stat-card">
          <div :style="{ position:'absolute',top:0,left:0,right:0,height:'3px',borderRadius:'0.875rem 0.875rem 0 0',background: critical > 0 ? '#ef4444' : '#10b981' }"></div>
          <div class="m-stat-icon" :style="{ background: critical > 0 ? '#fef2f2' : '#f0fdf4', color: critical > 0 ? '#ef4444' : '#059669' }">
            <i class="fa-solid fa-fire"></i>
          </div>
          <div class="m-stat-value" :style="{ color: critical > 0 ? '#ef4444' : '#111827' }">{{ critical }}</div>
          <div class="m-stat-label">Critical Defects</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#6366f1;"></div>
          <div class="m-stat-icon" style="background:#eef2ff;color:#6366f1">
            <i class="fa-solid fa-chart-pie"></i>
          </div>
          <div class="m-stat-value">{{ resolutionRate }}%</div>
          <div class="m-stat-label">Repair Rate</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#3b82f6;"></div>
          <div class="m-stat-icon" style="background:#eff6ff;color:#2563eb">
            <i class="fa-solid fa-clipboard-check"></i>
          </div>
          <div class="m-stat-value">{{ inspections.length }}</div>
          <div class="m-stat-label">Total Inspections</div>
        </div>

      </div>

      <!-- Charts -->
      <div class="m-charts-grid" style="margin-bottom:1.25rem">
        <div class="m-card m-chart-card">
          <div class="m-card-body">
            <p class="m-chart-title">Defects Reported Over Time</p>
            <div class="m-chart-body">
              <Line :data="trendChartData" :options="CHART_OPTS"/>
            </div>
          </div>
        </div>
        <div class="m-card m-chart-card">
          <div class="m-card-body">
            <p class="m-chart-title">Repair Status Breakdown</p>
            <div class="m-chart-body">
              <Doughnut :data="statusChartData" :options="CHART_OPTS_PIE"/>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent active defects -->
      <div class="m-card">
        <div class="m-card-header">
          <h3>Active Defects</h3>
          <button class="m-btn m-btn-secondary m-btn-sm" @click="router.push({ name: 'maintenance-faults' })">
            View All <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>

        <div v-if="recentFaults.length === 0" class="m-empty">
          <i class="fa-solid fa-circle-check" style="color:#10b981;font-size:2rem;display:block;margin-bottom:0.75rem;"></i>
          No active defects — all clear!
        </div>

        <div v-else class="m-table-wrap">
          <table class="m-table m-table-clickable">
            <thead>
              <tr>
                <th>Defect</th>
                <th>Part Location</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Inspection Date</th>
                <th>Checked By</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="f in recentFaults"
                :key="f.id"
                @click="router.push({ name: 'paint-inspection-view', params: { id: f.inspectionId } })"
              >
                <td style="font-weight:600;color:#111827;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                  {{ f.title }}
                </td>
                <td style="color:#6b7280;font-size:0.8125rem">{{ f.location || '—' }}</td>
                <td>
                  <span class="m-badge" :style="{ background: SEVERITY_COLOR[f.severity] + '22', color: SEVERITY_COLOR[f.severity] }">
                    {{ f.severity }}
                  </span>
                </td>
                <td>
                  <span class="m-badge" :style="{ background: statusBg(f.status), color: STATUS_COLOR[f.status] }">
                    {{ STATUS_LABEL[f.status] ?? f.status }}
                  </span>
                </td>
                <td style="color:#6b7280;font-size:0.8125rem">{{ fmtDate(f.createdAt) }}</td>
                <td style="color:#9ca3af;font-size:0.8125rem">{{ f.reporterName }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>
  </div>
</template>

<style scoped src="@/styles/pages/maintenance-dashboard.css"></style>
