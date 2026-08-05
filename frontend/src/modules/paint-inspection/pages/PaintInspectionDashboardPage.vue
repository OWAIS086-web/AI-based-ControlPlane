<script setup lang="ts">
import { usePaintDashboard } from '../composables/usePaintDashboard'
import VButton from '@/components/ui/VButton.vue'
import { computed } from 'vue'
import {
  Chart as ChartJS,
  ArcElement, CategoryScale, LinearScale,
  PointElement, LineElement, BarElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { Bar, Line, Doughnut, Pie } from 'vue-chartjs'
import type { ChartOptions } from 'chart.js'

ChartJS.register(ArcElement, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

const {
  loading, error, stats,
  defectsByTypeChart, defectsByPartChart, inspectionsByColorChart,
  repairRateChart, inspectionsTrendChart, repairVsLetGoChart,
  fetchDashboardData,
} = usePaintDashboard()

const overallRepairRate = computed(() => {
  const total = stats.value.totalRepairQty + stats.value.totalLetGoQty
  return total > 0 ? Math.round((stats.value.totalRepairQty / total) * 100) : 0
})

const barOpts: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: true, labels: { color: '#374151', font: { size: 12, weight: 'bold' } } },
    tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleColor: '#fff', bodyColor: '#fff', borderColor: '#3b82f6', borderWidth: 1 },
  },
  scales: {
    y: { beginAtZero: true, ticks: { color: '#6b7280' }, grid: { color: 'rgba(229,231,235,0.5)' } },
    x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(229,231,235,0.5)' } },
  },
}

const lineOpts: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: true, labels: { color: '#374151', font: { size: 12, weight: 'bold' } } },
    tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleColor: '#fff', bodyColor: '#fff', borderColor: '#3b82f6', borderWidth: 1 },
  },
  scales: {
    y: { beginAtZero: true, ticks: { color: '#6b7280' }, grid: { color: 'rgba(229,231,235,0.5)' } },
    x: { ticks: { color: '#6b7280' }, grid: { color: 'rgba(229,231,235,0.5)' } },
  },
}

const doughnutOpts: ChartOptions<'doughnut'> = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: true, labels: { color: '#374151', font: { size: 12, weight: 'bold' } } },
    tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleColor: '#fff', bodyColor: '#fff', borderColor: '#3b82f6', borderWidth: 1 },
  },
}

const pieOpts: ChartOptions<'pie'> = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: true, labels: { color: '#374151', font: { size: 12, weight: 'bold' } } },
    tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleColor: '#fff', bodyColor: '#fff', borderColor: '#3b82f6', borderWidth: 1 },
  },
}
</script>

<template>
  <div class="dashboard-page">
    <div class="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Header -->
      <div class="page-header mb-6">
        <div class="header-content">
          <div class="header-title">
            <i class="fa-solid fa-chart-line"></i>
            <h1>Paint Inspection Dashboard</h1>
          </div>
          <div class="header-actions">
            <VButton @click="fetchDashboardData" :disabled="loading">
              <i :class="loading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-rotate-right'"></i>
              {{ loading ? 'Refreshing...' : 'Refresh' }}
            </VButton>
          </div>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">
        <i class="fa-solid fa-circle-exclamation"></i>
        <span>{{ error }}</span>
      </div>

      <div v-if="loading" class="loading-state">
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Loading dashboard data...</p>
      </div>

      <div v-else class="dashboard-content">
        <!-- Stats -->
        <div class="stats-grid">
          <div class="stat-card premium">
            <div class="stat-icon total"><i class="fa-solid fa-file-check"></i></div>
            <div class="stat-content">
              <p class="stat-label">Total Inspections</p>
              <p class="stat-value">{{ stats.totalInspections }}</p>
              <p class="stat-trend">All time</p>
            </div>
          </div>
          <div class="stat-card premium">
            <div class="stat-icon defects"><i class="fa-solid fa-exclamation-triangle"></i></div>
            <div class="stat-content">
              <p class="stat-label">Total Defects</p>
              <p class="stat-value">{{ stats.totalDefects }}</p>
              <p class="stat-trend">{{ stats.averageDefectsPerInspection }} avg/inspection</p>
            </div>
          </div>
          <div class="stat-card premium">
            <div class="stat-icon repair"><i class="fa-solid fa-wrench"></i></div>
            <div class="stat-content">
              <p class="stat-label">Total Repaired</p>
              <p class="stat-value">{{ stats.totalRepairQty }}</p>
              <p class="stat-trend">{{ overallRepairRate }}% repair rate</p>
            </div>
          </div>
          <div class="stat-card premium">
            <div class="stat-icon letgo"><i class="fa-solid fa-check-circle"></i></div>
            <div class="stat-content">
              <p class="stat-label">Total Let Go</p>
              <p class="stat-value">{{ stats.totalLetGoQty }}</p>
              <p class="stat-trend">{{ 100 - overallRepairRate }}% let go</p>
            </div>
          </div>
          <div class="stat-card premium">
            <div class="stat-icon rate"><i class="fa-solid fa-percent"></i></div>
            <div class="stat-content">
              <p class="stat-label">Overall Repair Rate</p>
              <p class="stat-value">{{ overallRepairRate }}%</p>
              <p class="stat-trend">Quality metric</p>
            </div>
          </div>
          <div class="stat-card premium">
            <div class="stat-icon colors"><i class="fa-solid fa-palette"></i></div>
            <div class="stat-content">
              <p class="stat-label">Colors Inspected</p>
              <p class="stat-value">{{ Object.keys(stats.inspectionsByColor).length }}</p>
              <p class="stat-trend">Variety</p>
            </div>
          </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
          <div class="chart-card large">
            <div class="chart-header">
              <h2>Defects by Type</h2>
              <span class="chart-badge">{{ Object.keys(stats.defectsByType).length }} types</span>
            </div>
            <div class="chart-body"><Bar :data="defectsByTypeChart" :options="barOpts" /></div>
          </div>

          <div class="chart-card">
            <div class="chart-header"><h2>Repair vs Let Go</h2></div>
            <div class="chart-body"><Doughnut :data="repairVsLetGoChart" :options="doughnutOpts" /></div>
          </div>

          <div class="chart-card">
            <div class="chart-header"><h2>Inspections by Color</h2></div>
            <div class="chart-body"><Pie :data="inspectionsByColorChart" :options="pieOpts" /></div>
          </div>

          <div class="chart-card large">
            <div class="chart-header">
              <h2>Top 10 Defects by Part</h2>
              <span class="chart-badge">Vehicle parts</span>
            </div>
            <div class="chart-body"><Bar :data="defectsByPartChart" :options="barOpts" /></div>
          </div>

          <div class="chart-card large">
            <div class="chart-header">
              <h2>Top 10 Defects by Repair Rate</h2>
              <span class="chart-badge">Quality analysis</span>
            </div>
            <div class="chart-body"><Bar :data="repairRateChart" :options="barOpts" /></div>
          </div>

          <div class="chart-card full-width">
            <div class="chart-header">
              <h2>Inspections Over Time</h2>
              <span class="chart-badge">Trend analysis</span>
            </div>
            <div class="chart-body"><Line :data="inspectionsTrendChart" :options="lineOpts" /></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped src="@/styles/pages/paint-inspection-dashboard.css"></style>
