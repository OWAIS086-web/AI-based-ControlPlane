import { ref, computed } from 'vue'
import type { InspectionDefect } from '@/types/paint-inspection'

interface DefectOnPart {
  partPosition: string
  partName: string
  defectName: string
  quantity: number
  repairQty?: number
}

export function useDefectAggregation() {
  const defectsOnParts = ref<DefectOnPart[]>([])
  const inspectionDefects = ref<InspectionDefect[]>([])
  const isInitializing = ref(false)

  const addDefectToPart = (defect: DefectOnPart) => {
    const existingIndex = defectsOnParts.value.findIndex(
      (d) => d.partPosition === defect.partPosition && d.defectName === defect.defectName
    )
    if (existingIndex >= 0) {
      defectsOnParts.value[existingIndex].quantity += defect.quantity
    } else {
      defectsOnParts.value.push(defect)
    }
    if (!isInitializing.value) aggregateDefects()
  }

  const removeDefectFromPart = (partPosition: string, defectName: string) => {
    defectsOnParts.value = defectsOnParts.value.filter(
      (d) => !(d.partPosition === partPosition && d.defectName === defectName)
    )
    if (!isInitializing.value) aggregateDefects()
  }

  const updateDefectOnPart = (defect: DefectOnPart) => {
    const index = defectsOnParts.value.findIndex(
      (d) => d.partPosition === defect.partPosition && d.defectName === defect.defectName
    )
    if (index >= 0) defectsOnParts.value[index] = defect
    if (!isInitializing.value) aggregateDefects()
  }

  const aggregateDefects = () => {
    const defectMap = new Map<string, number>()
    const existingDefects = new Map<string, InspectionDefect>()

    inspectionDefects.value.forEach((defect) => {
      existingDefects.set(defect.name, defect)
    })

    defectsOnParts.value.forEach((defect) => {
      const current = defectMap.get(defect.defectName) || 0
      defectMap.set(defect.defectName, current + defect.quantity)
    })

    inspectionDefects.value = Array.from(defectMap.entries()).map(([name, totalQty], index) => {
      const existing = existingDefects.get(name)
      return {
        serial_no: index + 1,
        name,
        total_qty: totalQty,
        let_go_qty: existing?.let_go_qty ?? null,
        repair_qty: existing?.repair_qty ?? null,
        remarks: existing?.remarks ?? null,
      }
    })
  }

  const getDefectsForPart = (partPosition: string): DefectOnPart[] =>
    defectsOnParts.value.filter((d) => d.partPosition === partPosition)

  const getPartDefectCount = (partPosition: string): number =>
    getDefectsForPart(partPosition).reduce((sum, d) => sum + d.quantity, 0)

  const getTotalDefectCount = computed(() =>
    defectsOnParts.value.reduce((sum, d) => sum + d.quantity, 0)
  )

  const getUniqueDefectTypes = computed(() =>
    Array.from(new Set(defectsOnParts.value.map((d) => d.defectName)))
  )

  const getDefectSummary = computed(() => {
    const summary: Record<string, { count: number; parts: string[] }> = {}
    defectsOnParts.value.forEach((defect) => {
      if (!summary[defect.defectName]) {
        summary[defect.defectName] = { count: 0, parts: [] }
      }
      summary[defect.defectName].count += defect.quantity
      if (!summary[defect.defectName].parts.includes(defect.partName)) {
        summary[defect.defectName].parts.push(defect.partName)
      }
    })
    return summary
  })

  const clearAllDefects = () => {
    defectsOnParts.value = []
    inspectionDefects.value = []
  }

  const loadFromInspection = (defects: InspectionDefect[]) => {
    inspectionDefects.value = defects
  }

  const exportDefects = () =>
    inspectionDefects.value.map((defect) => ({
      serial_no: defect.serial_no,
      name: defect.name,
      total_qty: defect.total_qty,
      let_go_qty: defect.let_go_qty,
      repair_qty: defect.repair_qty,
      remarks: defect.remarks,
    }))

  const startInitialization = () => { isInitializing.value = true }

  const endInitialization = () => {
    isInitializing.value = false
    aggregateDefects()
  }

  return {
    defectsOnParts,
    inspectionDefects,
    addDefectToPart,
    removeDefectFromPart,
    updateDefectOnPart,
    getDefectsForPart,
    getPartDefectCount,
    getTotalDefectCount,
    getUniqueDefectTypes,
    getDefectSummary,
    clearAllDefects,
    loadFromInspection,
    exportDefects,
    startInitialization,
    endInitialization,
  }
}
