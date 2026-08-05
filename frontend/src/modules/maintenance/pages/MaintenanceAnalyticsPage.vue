<script setup lang="ts">
import { computed, onMounted } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import FaultLocationDiagram from '../components/FaultLocationDiagram.vue'
import { usePaintDashboard } from '@/modules/paint-inspection/composables/usePaintDashboard'
import type { FaultRecord } from '@/services/maintenanceApi'
import type { InspectionDefect } from '@/types/paint-inspection'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, PointElement, LineElement, Title, Tooltip, Legend, Filler)

// ── Paint inspection data source ─────────────────────────────────────
const { loading, inspections, fetchDashboardData } = usePaintDashboard()

// ── Severity mapping from defect type name ───────────────────────────
function defectSeverity(name: string): FaultRecord['severity'] {
  const n = name.toLowerCase()
  if (n.includes('crater'))                                         return 'critical'
  if (n.includes('dent') || n.includes('glass') || n.includes('less paint')) return 'high'
  if (n.includes('major') || n.includes('black') || n.includes('sag') || n.includes('orange')) return 'medium'
  return 'low'
}

// ── Status from repair/let-go qty ────────────────────────────────────
function defectStatus(d: InspectionDefect): FaultRecord['status'] {
  if ((d.repair_qty ?? 0) > 0) return 'resolved'
  if ((d.let_go_qty ?? 0) > 0) return 'open'
  return 'in_progress'
}

// ── Adapted faults: one per defect row, used for all charts ─────────
const allFaults = computed<FaultRecord[]>(() =>
  inspections.value.flatMap(insp =>
    insp.defects.map((d, i): FaultRecord => ({
      id:          `${insp.id}-${i}`,
      title:       d.name,
      description: d.remarks ?? '',
      location:    insp.vehicle_parts.find(p => p.annotation?.trim())?.part_name ?? null,
      severity:    defectSeverity(d.name),
      status:      defectStatus(d),
      reportedBy:  insp.created_by_id,
      reporterName: insp.checked_by ?? insp.created_by_id,
      assignedTo:  null,
      assigneeName: null,
      resolvedAt:  null,
      createdAt:   insp.created_at,
      updatedAt:   insp.updated_at,
    }))
  )
)

// ── Diagram faults: one per annotated vehicle part ───────────────────
// FaultLocationDiagram matches by f.location against part names
const diagramFaults = computed<FaultRecord[]>(() =>
  inspections.value.flatMap(insp =>
    insp.vehicle_parts
      .filter(p => p.annotation?.trim())
      .map((p, i): FaultRecord => ({
        id:          `${insp.id}-part-${i}`,
        title:       p.annotation!,
        description: '',
        location:    p.part_name,
        severity:    'medium',
        status:      'open',
        reportedBy:  insp.created_by_id,
        reporterName: insp.checked_by ?? '',
        assignedTo:  null,
        assigneeName: null,
        resolvedAt:  null,
        createdAt:   insp.created_at,
        updatedAt:   insp.updated_at,
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

const severityChartData = computed(() => {
  const c = { low: 0, medium: 0, high: 0, critical: 0 }
  allFaults.value.forEach(f => c[f.severity]++)
  return {
    labels: ['Low', 'Medium', 'High', 'Critical'],
    datasets: [{
      label: 'Defects',
      data: [c.low, c.medium, c.high, c.critical],
      backgroundColor: ['#10b98166', '#f59e0b66', '#f9731666', '#ef444466'],
      borderColor:     ['#10b981',   '#f59e0b',   '#f97316',   '#ef4444'],
      borderWidth: 2,
      borderRadius: 6,
    }],
  }
})

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

const stackedStatusChartData = computed(() => {
  const byMonth: Record<string, { open: number; in_progress: number; resolved: number }> = {}
  allFaults.value.forEach(f => {
    const key = new Date(f.createdAt).toLocaleDateString('en-GB', { month: 'short', year: '2-digit' })
    if (!byMonth[key]) byMonth[key] = { open: 0, in_progress: 0, resolved: 0 }
    byMonth[key][f.status]++
  })
  const labels = Object.keys(byMonth).slice(-8)
  return {
    labels,
    datasets: [
      { label: 'Let Go',   data: labels.map(l => byMonth[l]?.open        ?? 0), backgroundColor: '#ef444466', borderColor: '#ef4444', borderWidth: 1, borderRadius: 4 },
      { label: 'Pending',  data: labels.map(l => byMonth[l]?.in_progress ?? 0), backgroundColor: '#f59e0b66', borderColor: '#f59e0b', borderWidth: 1, borderRadius: 4 },
      { label: 'Repaired', data: labels.map(l => byMonth[l]?.resolved    ?? 0), backgroundColor: '#10b98166', borderColor: '#10b981', borderWidth: 1, borderRadius: 4 },
    ],
  }
})

const locationsChartData = computed(() => {
  const counts: Record<string, number> = {}
  inspections.value.forEach(insp =>
    insp.vehicle_parts.filter(p => p.annotation?.trim()).forEach(p => {
      counts[p.part_name] = (counts[p.part_name] ?? 0) + 1
    })
  )
  const sorted = Object.entries(counts).sort(([, a], [, b]) => b - a).slice(0, 8)
  return {
    labels: sorted.map(([loc]) => loc),
    datasets: [{
      label: 'Defects',
      data: sorted.map(([, c]) => c),
      backgroundColor: '#6366f166',
      borderColor: '#6366f1',
      borderWidth: 2,
      borderRadius: 6,
    }],
  }
})

const resolutionBySeverityChartData = computed(() => {
  const data: Record<string, { total: number; resolved: number }> = {
    low: { total: 0, resolved: 0 }, medium: { total: 0, resolved: 0 },
    high: { total: 0, resolved: 0 }, critical: { total: 0, resolved: 0 },
  }
  allFaults.value.forEach(f => {
    data[f.severity].total++
    if (f.status === 'resolved') data[f.severity].resolved++
  })
  return {
    labels: ['Low', 'Medium', 'High', 'Critical'],
    datasets: [{
      label: 'Repair Rate %',
      data: Object.values(data).map(d => d.total ? Math.round((d.resolved / d.total) * 100) : 0),
      backgroundColor: ['#10b98166', '#f59e0b66', '#f9731666', '#ef444466'],
      borderColor:     ['#10b981',   '#f59e0b',   '#f97316',   '#ef4444'],
      borderWidth: 2,
      borderRadius: 6,
    }],
  }
})

function resolutionTable() {
  const data: Record<string, { label: string; total: number; resolved: number; color: string }> = {
    critical: { label: 'Critical', total: 0, resolved: 0, color: '#ef4444' },
    high:     { label: 'High',     total: 0, resolved: 0, color: '#f97316' },
    medium:   { label: 'Medium',   total: 0, resolved: 0, color: '#f59e0b' },
    low:      { label: 'Low',      total: 0, resolved: 0, color: '#10b981' },
  }
  allFaults.value.forEach(f => {
    data[f.severity].total++
    if (f.status === 'resolved') data[f.severity].resolved++
  })
  return Object.values(data).map(d => ({
    ...d,
    rate: d.total ? Math.round((d.resolved / d.total) * 100) : 0,
  }))
}

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
  plugins: { legend: { position: 'bottom' as const, labels: { color: '#374151', font: { size: 11 }, padding: 16 } } },
}
const CHART_OPTS_STACKED = {
  ...CHART_OPTS,
  scales: {
    x: { stacked: true, ticks: { color: '#6b7280' }, grid: { color: '#f3f4f6' } },
    y: { stacked: true, ticks: { color: '#6b7280' }, grid: { color: '#f3f4f6' }, beginAtZero: true },
  },
}
</script>

<template>
  <div class="m-analytics">

    <!-- Header -->
    <div class="m-page-header">
      <div class="m-page-header-text">
        <h1>Fault Analytics</h1>
        <p>Defect insights, trends and vehicle location diagram from paint inspections</p>
      </div>
      <button class="m-btn m-btn-secondary" :disabled="loading" @click="fetchDashboardData">
        <i v-if="loading" class="fa-solid fa-spinner fa-spin"></i>
        <i v-else class="fa-solid fa-rotate-right"></i>
        Refresh
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="m-loading">
      <i class="fa-solid fa-spinner fa-spin"></i> Loading analytics…
    </div>

    <template v-else>

      <!-- KPI grid -->
      <div class="m-stat-grid">

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#f59e0b;"></div>
          <div class="m-stat-icon" style="background:#fffbeb;color:#d97706"><i class="fa-solid fa-triangle-exclamation"></i></div>
          <div class="m-stat-value">{{ total }}</div>
          <div class="m-stat-label">Total Defects</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#ef4444;"></div>
          <div class="m-stat-icon" style="background:#fef2f2;color:#ef4444"><i class="fa-solid fa-circle-dot"></i></div>
          <div class="m-stat-value">{{ openCount }}</div>
          <div class="m-stat-label">Let Go</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#f59e0b;"></div>
          <div class="m-stat-icon" style="background:#fffbeb;color:#d97706"><i class="fa-solid fa-clock-rotate-left"></i></div>
          <div class="m-stat-value">{{ inProgress }}</div>
          <div class="m-stat-label">Pending</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#10b981;"></div>
          <div class="m-stat-icon" style="background:#f0fdf4;color:#059669"><i class="fa-solid fa-circle-check"></i></div>
          <div class="m-stat-value">{{ resolved }}</div>
          <div class="m-stat-label">Repaired</div>
        </div>

        <div class="m-stat-card">
          <div :style="{ position:'absolute',top:0,left:0,right:0,height:'3px',borderRadius:'0.875rem 0.875rem 0 0',background: critical > 0 ? '#ef4444' : '#10b981' }"></div>
          <div class="m-stat-icon" :style="{ background: critical > 0 ? '#fef2f2' : '#f0fdf4', color: critical > 0 ? '#ef4444' : '#059669' }">
            <i class="fa-solid fa-fire"></i>
          </div>
          <div class="m-stat-value" :style="{ color: critical > 0 ? '#ef4444' : '#111827' }">{{ critical }}</div>
          <div class="m-stat-label">Critical</div>
        </div>

        <div class="m-stat-card">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;border-radius:0.875rem 0.875rem 0 0;background:#6366f1;"></div>
          <div class="m-stat-icon" style="background:#eef2ff;color:#6366f1"><i class="fa-solid fa-percent"></i></div>
          <div class="m-stat-value">{{ resolutionRate }}%</div>
          <div class="m-stat-label">Repair Rate</div>
        </div>

      </div>

      <!-- Vehicle diagram -->
      <div class="m-diagram-card">
        <h3><i class="fa-solid fa-car" style="color:#f59e0b;margin-right:0.5rem"></i>Defect Location Diagram</h3>
        <p>Parts highlighted in red have recorded defect annotations. Hover to see details.</p>
        <FaultLocationDiagram :faults="diagramFaults" :readonly="true"/>
      </div>

      <!-- Row 1: Trend + Status -->
      <div class="m-charts-row m-charts-row-3-1">
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Defects Reported Over Time (by week)</p>
            <div class="m-chart-body-md">
              <Line :data="trendChartData" :options="CHART_OPTS"/>
            </div>
          </div>
        </div>
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Repair Status</p>
            <div class="m-chart-body-md">
              <Doughnut :data="statusChartData" :options="CHART_OPTS_PIE"/>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 2: Severity + Resolution rate -->
      <div class="m-charts-row m-charts-row-2">
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Defects by Severity</p>
            <div class="m-chart-body-sm">
              <Bar :data="severityChartData" :options="CHART_OPTS"/>
            </div>
          </div>
        </div>
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Repair Rate by Severity (%)</p>
            <div class="m-chart-body-sm">
              <Bar :data="resolutionBySeverityChartData" :options="CHART_OPTS"/>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 3: Stacked monthly + Top part locations -->
      <div class="m-charts-row m-charts-row-2">
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Defect Status by Month (stacked)</p>
            <div class="m-chart-body-sm">
              <Bar :data="stackedStatusChartData" :options="CHART_OPTS_STACKED"/>
            </div>
          </div>
        </div>
        <div class="m-card">
          <div class="m-card-body">
            <p class="m-chart-title">Top 8 Affected Parts</p>
            <div v-if="locationsChartData.labels.length === 0" class="m-empty" style="height:220px;display:flex;align-items:center;justify-content:center">
              No part annotation data recorded.
            </div>
            <div v-else class="m-chart-body-sm">
              <Bar :data="locationsChartData" :options="CHART_OPTS"/>
            </div>
          </div>
        </div>
      </div>

      <!-- Resolution analysis table -->
      <div class="m-card" style="margin-bottom:1.25rem">
        <div class="m-card-body">
          <p class="m-chart-title">Repair Analysis by Severity</p>
          <div class="m-table-wrap">
            <table class="m-table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Total Defects</th>
                  <th>Repaired</th>
                  <th>Let Go / Pending</th>
                  <th style="min-width:140px">Repair Rate</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in resolutionTable()" :key="row.label">
                  <td>
                    <span class="m-badge" :style="{ background: row.color + '22', color: row.color }">
                      {{ row.label }}
                    </span>
                  </td>
                  <td style="font-weight:700">{{ row.total }}</td>
                  <td style="color:#059669;font-weight:600">{{ row.resolved }}</td>
                  <td style="color:#6b7280">{{ row.total - row.resolved }}</td>
                  <td>
                    <div style="display:flex;align-items:center;gap:0.75rem">
                      <div class="m-progress-bar-wrap">
                        <div class="m-progress-bar-fill" :style="{ width: row.rate + '%', background: row.color }"></div>
                      </div>
                      <span style="font-weight:700;font-size:0.8125rem;min-width:36px;text-align:right">{{ row.rate }}%</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Key metrics -->
      <div class="m-metrics-grid">
        <div class="m-metric-card">
          <div class="m-metric-value" style="color:#f59e0b">{{ total }}</div>
          <div class="m-metric-label">Total Defects</div>
          <div class="m-metric-sub">all time</div>
        </div>
        <div class="m-metric-card">
          <div class="m-metric-value" style="color:#10b981">{{ resolutionRate }}%</div>
          <div class="m-metric-label">Repair Rate</div>
          <div class="m-metric-sub">repaired / total</div>
        </div>
        <div class="m-metric-card">
          <div class="m-metric-value" style="color:#6366f1">{{ inspections.length }}</div>
          <div class="m-metric-label">Inspections</div>
          <div class="m-metric-sub">total records</div>
        </div>
        <div class="m-metric-card">
          <div class="m-metric-value" :style="{ color: critical > 0 ? '#ef4444' : '#10b981' }">{{ critical }}</div>
          <div class="m-metric-label">Critical Defects</div>
          <div class="m-metric-sub">need immediate action</div>
        </div>
      </div>

    </template>
  </div>
</template>

<style scoped src="@/styles/pages/maintenance-analytics.css"></style>
