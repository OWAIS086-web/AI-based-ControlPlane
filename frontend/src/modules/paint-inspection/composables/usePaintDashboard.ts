import { ref, computed, onMounted } from 'vue'
import { paintInspectionService } from '@/services/paint-inspection.service'
import type { PaintInspection } from '@/types/paint-inspection'

interface DashboardStats {
  totalInspections: number
  totalDefects: number
  averageDefectsPerInspection: number
  totalRepairQty: number
  totalLetGoQty: number
  defectsByType: Record<string, number>
  defectsByPart: Record<string, number>
  inspectionsByColor: Record<string, number>
  inspectionsByDate: Record<string, number>
  repairRateByDefect: Record<string, { total: number; repaired: number; rate: number }>
  inspections?: PaintInspection[]
}

interface ChartData {
  labels: string[]
  datasets: Array<{
    label: string
    data: number[]
    backgroundColor?: string | string[]
    borderColor?: string
    borderWidth?: number
    fill?: boolean
    tension?: number
  }>
}

export function usePaintDashboard() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const inspections = ref<PaintInspection[]>([])
  const stats = ref<DashboardStats>({
    totalInspections: 0,
    totalDefects: 0,
    averageDefectsPerInspection: 0,
    totalRepairQty: 0,
    totalLetGoQty: 0,
    defectsByType: {},
    defectsByPart: {},
    inspectionsByColor: {},
    inspectionsByDate: {},
    repairRateByDefect: {},
    inspections: [],
  })

  const defectsByTypeChart = computed<ChartData>(() => {
    const labels = Object.keys(stats.value.defectsByType).sort(
      (a, b) => stats.value.defectsByType[b] - stats.value.defectsByType[a]
    )
    return {
      labels,
      datasets: [{
        label: 'Defects by Type',
        data: labels.map((l) => stats.value.defectsByType[l]),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 2,
      }],
    }
  })

  const defectsByPartChart = computed<ChartData>(() => {
    const labels = Object.keys(stats.value.defectsByPart)
      .sort((a, b) => stats.value.defectsByPart[b] - stats.value.defectsByPart[a])
      .slice(0, 10)
    return {
      labels,
      datasets: [{
        label: 'Defects by Part',
        data: labels.map((l) => stats.value.defectsByPart[l]),
        backgroundColor: [
          'rgba(59,130,246,0.8)', 'rgba(139,92,246,0.8)', 'rgba(6,182,212,0.8)',
          'rgba(16,185,129,0.8)', 'rgba(245,158,11,0.8)', 'rgba(239,68,68,0.8)',
          'rgba(168,85,247,0.8)', 'rgba(236,72,153,0.8)', 'rgba(14,165,233,0.8)',
          'rgba(34,197,94,0.8)',
        ],
        borderColor: 'rgba(255,255,255,0.2)',
        borderWidth: 2,
      }],
    }
  })

  const inspectionsByColorChart = computed<ChartData>(() => {
    const labels = Object.keys(stats.value.inspectionsByColor).sort(
      (a, b) => stats.value.inspectionsByColor[b] - stats.value.inspectionsByColor[a]
    )
    return {
      labels,
      datasets: [{
        label: 'Inspections by Color',
        data: labels.map((l) => stats.value.inspectionsByColor[l]),
        backgroundColor: [
          'rgba(59,130,246,0.8)', 'rgba(139,92,246,0.8)', 'rgba(6,182,212,0.8)',
          'rgba(16,185,129,0.8)', 'rgba(245,158,11,0.8)', 'rgba(239,68,68,0.8)',
          'rgba(168,85,247,0.8)', 'rgba(236,72,153,0.8)',
        ],
        borderColor: 'rgba(255,255,255,0.2)',
        borderWidth: 2,
      }],
    }
  })

  const repairRateChart = computed<ChartData>(() => {
    const labels = Object.keys(stats.value.repairRateByDefect)
      .sort((a, b) => stats.value.repairRateByDefect[b].rate - stats.value.repairRateByDefect[a].rate)
      .slice(0, 10)
    return {
      labels,
      datasets: [{
        label: 'Repair Rate (%)',
        data: labels.map((l) => Math.round(stats.value.repairRateByDefect[l].rate * 100)),
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 2,
      }],
    }
  })

  const inspectionsTrendChart = computed<ChartData>(() => {
    const sortedDates = Object.keys(stats.value.inspectionsByDate).sort()
    return {
      labels: sortedDates,
      datasets: [{
        label: 'Inspections Over Time',
        data: sortedDates.map((d) => stats.value.inspectionsByDate[d]),
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
      }],
    }
  })

  const repairVsLetGoChart = computed<ChartData>(() => ({
    labels: ['Repaired', 'Let Go'],
    datasets: [{
      label: 'Defects Status',
      data: [stats.value.totalRepairQty, stats.value.totalLetGoQty],
      backgroundColor: ['rgba(16,185,129,0.8)', 'rgba(139,92,246,0.8)'],
      borderColor: 'rgba(255,255,255,0.2)',
      borderWidth: 2,
    }],
  }))

  const fetchDashboardData = async () => {
    loading.value = true
    error.value = null
    try {
      let allInspections: PaintInspection[] = []
      let page = 1
      let hasMore = true
      while (hasMore) {
        const response = await paintInspectionService.getList({ page, page_size: 100 })
        allInspections = [...allInspections, ...response.items]
        hasMore = page < response.total_pages
        page++
      }
      inspections.value = allInspections
      calculateStats(allInspections)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to load dashboard data'
    } finally {
      loading.value = false
    }
  }

  const calculateStats = (list: PaintInspection[]) => {
    const s: DashboardStats = {
      totalInspections: list.length,
      totalDefects: 0,
      averageDefectsPerInspection: 0,
      totalRepairQty: 0,
      totalLetGoQty: 0,
      defectsByType: {},
      defectsByPart: {},
      inspectionsByColor: {},
      inspectionsByDate: {},
      repairRateByDefect: {},
      inspections: list,
    }

    list.forEach((inspection) => {
      s.inspectionsByColor[inspection.color] = (s.inspectionsByColor[inspection.color] || 0) + 1
      const dateKey = new Date(inspection.inspection_date).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      })
      s.inspectionsByDate[dateKey] = (s.inspectionsByDate[dateKey] || 0) + 1

      inspection.defects.forEach((defect) => {
        s.totalDefects++
        s.defectsByType[defect.name] = (s.defectsByType[defect.name] || 0) + 1
        s.totalRepairQty += Number(defect.repair_qty) || 0
        s.totalLetGoQty += Number(defect.let_go_qty) || 0
        if (!s.repairRateByDefect[defect.name]) {
          s.repairRateByDefect[defect.name] = { total: 0, repaired: 0, rate: 0 }
        }
        s.repairRateByDefect[defect.name].total += Number(defect.total_qty) || 0
        s.repairRateByDefect[defect.name].repaired += Number(defect.repair_qty) || 0
      })

      inspection.vehicle_parts.forEach((part) => {
        if (part.annotation && part.annotation.trim() !== '') {
          s.defectsByPart[part.part_name] = (s.defectsByPart[part.part_name] || 0) + 1
        }
      })
    })

    s.averageDefectsPerInspection = s.totalInspections > 0
      ? Math.round((s.totalDefects / s.totalInspections) * 100) / 100
      : 0

    Object.keys(s.repairRateByDefect).forEach((name) => {
      const d = s.repairRateByDefect[name]
      d.rate = d.total > 0 ? d.repaired / d.total : 0
    })

    stats.value = s
  }

  onMounted(() => {
    fetchDashboardData()
  })

  return {
    loading,
    error,
    inspections,
    stats,
    defectsByTypeChart,
    defectsByPartChart,
    inspectionsByColorChart,
    repairRateChart,
    inspectionsTrendChart,
    repairVsLetGoChart,
    fetchDashboardData,
  }
}
