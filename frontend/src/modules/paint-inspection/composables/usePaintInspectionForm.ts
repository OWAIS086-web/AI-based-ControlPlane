import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { paintInspectionService } from '@/services/paint-inspection.service'
import type {
  PaintInspectionCreate,
  PaintInspectionUpdate,
  InspectionDefect,
  VehiclePart,
} from '@/types/paint-inspection'
import { DEFAULT_DEFECT_TYPES } from '@/types/paint-inspection'

export function usePaintInspectionForm() {
  const router = useRouter()
  const route = useRoute()

  const loading = ref(false)
  const error = ref<string | null>(null)
  const success = ref(false)
  const isEditMode = ref(false)
  const inspectionId = ref<number | null>(null)

  const inspectionDate = ref(new Date().toISOString().split('T')[0])
  const paintingDate = ref(new Date().toISOString().split('T')[0])
  const ovenOutTime = ref('')
  const color = ref('')
  const vinNo = ref('')

  const defects = ref<Omit<InspectionDefect, 'id' | 'inspection_id' | 'created_at' | 'updated_at'>[]>(
    DEFAULT_DEFECT_TYPES.map((name, index) => ({
      serial_no: index + 1,
      name,
      total_qty: null,
      let_go_qty: null,
      repair_qty: null,
      remarks: null,
    }))
  )

  const vehicleParts = ref<Omit<VehiclePart, 'id' | 'inspection_id' | 'created_at'>[]>([])

  const checkedBy = ref('')
  const confirmedBy = ref('')
  const approvedBy = ref('')

  const totalProblems = computed(() =>
    defects.value.reduce((sum, d) => sum + (Number(d.total_qty) || 0), 0)
  )

  const repairProblems = computed(() =>
    defects.value.reduce((sum, d) => sum + (Number(d.repair_qty) || 0), 0)
  )

  const isFormValid = computed(() =>
    inspectionDate.value && paintingDate.value && color.value.trim() !== '' && vinNo.value.trim() !== ''
  )

  const addDefect = () => {
    defects.value.push({
      serial_no: defects.value.length + 1,
      name: '',
      total_qty: null,
      let_go_qty: null,
      repair_qty: null,
      remarks: null,
    })
  }

  const removeDefect = (index: number) => {
    defects.value.splice(index, 1)
    defects.value.forEach((d, idx) => { d.serial_no = idx + 1 })
  }

  const addVehiclePart = (
    partCode: string,
    partName: string,
    position: VehiclePart['position'],
    annotation: string
  ) => {
    const existingIndex = vehicleParts.value.findIndex(
      (p) => p.part_code === partCode && p.position === position
    )
    if (existingIndex >= 0) {
      vehicleParts.value[existingIndex].annotation = annotation
    } else {
      vehicleParts.value.push({ part_code: partCode, part_name: partName, position, annotation })
    }
  }

  const removeVehiclePart = (partCode: string, position: string) => {
    const index = vehicleParts.value.findIndex(
      (p) => p.part_code === partCode && p.position === position
    )
    if (index >= 0) vehicleParts.value.splice(index, 1)
  }

  const resetForm = () => {
    inspectionDate.value = new Date().toISOString().split('T')[0]
    paintingDate.value = new Date().toISOString().split('T')[0]
    ovenOutTime.value = ''
    color.value = ''
    vinNo.value = ''
    defects.value = DEFAULT_DEFECT_TYPES.map((name, index) => ({
      serial_no: index + 1, name, total_qty: null, let_go_qty: null, repair_qty: null, remarks: null,
    }))
    vehicleParts.value = []
    checkedBy.value = ''
    confirmedBy.value = ''
    approvedBy.value = ''
    error.value = null
    success.value = false
  }

  const loadInspection = async (id: number) => {
    loading.value = true
    error.value = null
    try {
      const inspection = await paintInspectionService.getById(id)
      inspectionDate.value = inspection.inspection_date
      paintingDate.value = inspection.painting_date
      ovenOutTime.value = inspection.oven_out_time || ''
      color.value = inspection.color
      vinNo.value = inspection.vin_no
      checkedBy.value = inspection.checked_by || ''
      confirmedBy.value = inspection.confirmed_by || ''
      approvedBy.value = inspection.approved_by || ''
      defects.value = inspection.defects.map((d) => ({
        serial_no: d.serial_no,
        name: d.name,
        total_qty: d.total_qty,
        let_go_qty: d.let_go_qty,
        repair_qty: d.repair_qty,
        remarks: d.remarks,
      }))
      vehicleParts.value = inspection.vehicle_parts.map((vp) => ({
        part_code: vp.part_code,
        part_name: vp.part_name,
        position: vp.position,
        annotation: vp.annotation,
      }))
      isEditMode.value = true
      inspectionId.value = id
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to load inspection'
    } finally {
      loading.value = false
    }
  }

  const submitForm = async () => {
    if (!isFormValid.value) {
      error.value = 'Please fill in all required fields'
      return
    }
    loading.value = true
    error.value = null
    success.value = false
    try {
      const data: PaintInspectionCreate | PaintInspectionUpdate = {
        inspection_date: inspectionDate.value,
        painting_date: paintingDate.value,
        oven_out_time: ovenOutTime.value || null,
        color: color.value,
        vin_no: vinNo.value,
        checked_by: checkedBy.value || null,
        confirmed_by: confirmedBy.value || null,
        approved_by: approvedBy.value || null,
        defects: defects.value.filter((d) => d.name.trim() !== ''),
        vehicle_parts: vehicleParts.value,
      }
      if (isEditMode.value && inspectionId.value) {
        await paintInspectionService.update(inspectionId.value, data)
      } else {
        await paintInspectionService.create(data)
      }
      success.value = true
      setTimeout(() => { router.push('/maintenance/paint-inspection/history') }, 1500)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : `Failed to ${isEditMode.value ? 'update' : 'create'} inspection`
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    const id = route.params.id
    if (id && typeof id === 'string') {
      const numId = Number(id)
      if (!isNaN(numId)) loadInspection(numId)
    }
  })

  return {
    loading, error, success, isEditMode, inspectionId,
    inspectionDate, paintingDate, ovenOutTime, color, vinNo,
    defects, vehicleParts, checkedBy, confirmedBy, approvedBy,
    totalProblems, repairProblems, isFormValid,
    addDefect, removeDefect, addVehiclePart, removeVehiclePart,
    resetForm, loadInspection, submitForm,
  }
}
