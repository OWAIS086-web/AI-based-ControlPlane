import { ref, computed } from 'vue'
import { maintenanceFaultService, type FaultRecord } from '@/services/maintenanceApi'

export function useMaintenanceDashboard() {
  const loading    = ref(false)
  const error      = ref<string | null>(null)
  const allFaults  = ref<FaultRecord[]>([])

  async function fetchAll() {
    loading.value = true
    error.value   = null
    allFaults.value = []
    try {
      let page = 1
      let hasMore = true
      while (hasMore) {
        const res = await maintenanceFaultService.list({ page, page_size: 100 })
        allFaults.value.push(...res.data)
        hasMore = page < res.meta.totalPages
        page++
      }
    } catch (e: any) {
      error.value = e.message ?? 'Failed to load faults'
    } finally {
      loading.value = false
    }
  }

  // ── Core counts ──────────────────────────────────────────────────────────────
  const total      = computed(() => allFaults.value.length)
  const openCount  = computed(() => allFaults.value.filter(f => f.status === 'open').length)
  const inProgress = computed(() => allFaults.value.filter(f => f.status === 'in_progress').length)
  const resolved   = computed(() => allFaults.value.filter(f => f.status === 'resolved').length)
  const critical   = computed(() => allFaults.value.filter(f => f.severity === 'critical').length)

  const resolutionRate = computed(() =>
    total.value ? Math.round((resolved.value / total.value) * 100) : 0,
  )

  const avgResolutionLabel = computed(() => {
    const resolvedFaults = allFaults.value.filter(f => f.status === 'resolved' && f.resolvedAt)
    if (!resolvedFaults.length) return '—'
    const totalMs = resolvedFaults.reduce(
      (acc, f) => acc + (new Date(f.resolvedAt!).getTime() - new Date(f.createdAt).getTime()), 0,
    )
    const hours = totalMs / resolvedFaults.length / 3_600_000
    return hours < 24 ? `${Math.round(hours)}h` : `${Math.round(hours / 24)}d`
  })

  const recentFaults = computed(() =>
    [...allFaults.value]
      .filter(f => f.status !== 'resolved')
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 8),
  )

  // ── Chart data ────────────────────────────────────────────────────────────────

  const statusChartData = computed(() => ({
    labels: ['Open', 'In Progress', 'Resolved'],
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
        label: 'Faults',
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
    allFaults.value.forEach(f => {
      const d   = new Date(f.createdAt)
      const day = d.getDay()
      const diff = d.getDate() - day + (day === 0 ? -6 : 1)
      const mon = new Date(new Date(f.createdAt).setDate(diff))
      const key = mon.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
      byWeek[key] = (byWeek[key] ?? 0) + 1
    })
    const sorted = Object.entries(byWeek).slice(-12)
    return {
      labels: sorted.map(([k]) => k),
      datasets: [{
        label: 'Faults reported',
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
        { label: 'Open',        data: labels.map(l => byMonth[l]?.open        ?? 0), backgroundColor: '#ef444466', borderColor: '#ef4444', borderWidth: 1, borderRadius: 4 },
        { label: 'In Progress', data: labels.map(l => byMonth[l]?.in_progress ?? 0), backgroundColor: '#f59e0b66', borderColor: '#f59e0b', borderWidth: 1, borderRadius: 4 },
        { label: 'Resolved',    data: labels.map(l => byMonth[l]?.resolved    ?? 0), backgroundColor: '#10b98166', borderColor: '#10b981', borderWidth: 1, borderRadius: 4 },
      ],
    }
  })

  const locationsChartData = computed(() => {
    const counts: Record<string, number> = {}
    allFaults.value.forEach(f => { if (f.location) counts[f.location] = (counts[f.location] ?? 0) + 1 })
    const sorted = Object.entries(counts).sort(([, a], [, b]) => b - a).slice(0, 8)
    return {
      labels: sorted.map(([loc]) => loc),
      datasets: [{
        label: 'Faults',
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
        label: 'Resolution Rate %',
        data: Object.values(data).map(d => d.total ? Math.round((d.resolved / d.total) * 100) : 0),
        backgroundColor: ['#10b98166', '#f59e0b66', '#f9731666', '#ef444466'],
        borderColor:     ['#10b981',   '#f59e0b',   '#f97316',   '#ef4444'],
        borderWidth: 2,
        borderRadius: 6,
      }],
    }
  })

  return {
    loading, error, allFaults,
    total, openCount, inProgress, resolved, critical,
    resolutionRate, avgResolutionLabel, recentFaults,
    fetchAll,
    statusChartData,
    severityChartData,
    trendChartData,
    stackedStatusChartData,
    locationsChartData,
    resolutionBySeverityChartData,
  }
}
