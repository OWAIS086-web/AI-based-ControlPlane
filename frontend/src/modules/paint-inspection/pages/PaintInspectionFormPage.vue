<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { usePaintInspectionForm } from '../composables/usePaintInspectionForm'
import { useDefectAggregation } from '../composables/useDefectAggregation'
import Vehicle3DViewer from '../components/Vehicle3DViewer.vue'
import DefectsTable from '../components/DefectsTable.vue'
import VButton from '@/components/ui/VButton.vue'

const {
  loading, error, success, isEditMode,
  inspectionDate, paintingDate, ovenOutTime, color, vinNo,
  defects, vehicleParts, checkedBy, confirmedBy, approvedBy,
  isFormValid, addDefect, removeDefect, addVehiclePart, removeVehiclePart,
  resetForm, submitForm,
} = usePaintInspectionForm()

const {
  defectsOnParts, inspectionDefects,
  addDefectToPart, removeDefectFromPart, updateDefectOnPart,
  startInitialization, endInitialization,
} = useDefectAggregation()

const showDiagram = ref(true)

const computedTotalProblems = computed(() =>
  inspectionDefects.value.reduce((sum, d) => sum + (Number(d.total_qty) || 0), 0)
)

watch(
  () => defectsOnParts.value,
  (newDefectsOnParts) => {
    const positionMap: Record<string, 'left' | 'front' | 'rear' | 'right' | 'top' | 'hood' | 'roof' | 'trunk' | 'door-left-front' | 'door-left-rear' | 'door-right-front' | 'door-right-rear' | 'fender-left' | 'fender-right' | 'bumper-front' | 'bumper-rear'> = {
      'left-front-fender': 'fender-left',
      'left-front-door': 'door-left-front',
      'right-front-fender': 'fender-right',
      'right-front-door': 'door-right-front',
      'left-rear-door': 'door-left-rear',
      'left-rear-quarter': 'left',
      'right-rear-door': 'door-right-rear',
      'right-rear-quarter': 'right',
      'front-grille': 'front',
      'bonnet': 'hood',
      'roof': 'roof',
      'rear-spoiler': 'rear',
      'tailgate': 'trunk',
      'bumper': 'bumper-rear',
      'rear-diffuser': 'bumper-rear',
    }
    vehicleParts.value = newDefectsOnParts.map((defect) => ({
      part_code: defect.partPosition,
      part_name: defect.partName,
      position: positionMap[defect.partPosition] || 'front',
      annotation: defect.defectName,
    }))
  },
  { deep: true }
)

watch(
  () => inspectionDefects.value,
  (newInspectionDefects) => {
    defects.value = newInspectionDefects.map((defect) => ({
      serial_no: defect.serial_no,
      name: defect.name,
      total_qty: defect.total_qty,
      let_go_qty: defect.let_go_qty,
      repair_qty: defect.repair_qty,
      remarks: defect.remarks,
    }))
  },
  { deep: true }
)

onMounted(() => {
  setTimeout(() => {
    startInitialization()
    if (isEditMode.value && defects.value.length > 0) {
      inspectionDefects.value = defects.value.map((defect) => ({
        serial_no: defect.serial_no,
        name: defect.name,
        total_qty: defect.total_qty,
        let_go_qty: defect.let_go_qty,
        repair_qty: defect.repair_qty,
        remarks: defect.remarks,
      }))
    }
    if (vehicleParts.value.length > 0) {
      vehicleParts.value.forEach((part) => {
        if (part.annotation && part.annotation.trim() !== '') {
          addDefectToPart({
            partPosition: part.part_code,
            partName: part.part_name,
            defectName: part.annotation,
            quantity: 1,
            repairQty: 0,
          })
        }
      })
    }
    endInitialization()
  }, 100)
})
</script>

<template>
  <div class="paint-inspection-page">
    <div class="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Header -->
      <div class="page-header mb-6">
        <div class="header-content">
          <div class="header-title">
            <i class="fa-solid fa-clipboard-check"></i>
            <h1>{{ isEditMode ? 'Edit' : 'New' }} Paint Inspection Sheet</h1>
          </div>
          <div class="header-actions">
            <VButton variant="secondary" @click="resetForm" :disabled="loading">
              <i class="fa-solid fa-rotate-right"></i>
              Reset
            </VButton>
            <VButton @click="submitForm" :disabled="!isFormValid || loading">
              <i :class="loading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-save'"></i>
              {{ loading ? 'Saving...' : (isEditMode ? 'Update' : 'Save') + ' Inspection' }}
            </VButton>
          </div>
        </div>
      </div>

      <div v-if="success" class="alert alert-success">
        <i class="fa-solid fa-circle-check"></i>
        <span>Inspection {{ isEditMode ? 'updated' : 'saved' }} successfully!</span>
      </div>

      <div v-if="error" class="alert alert-error">
        <i class="fa-solid fa-circle-exclamation"></i>
        <span>{{ error }}</span>
      </div>

      <div class="form-content">
        <!-- Header Info -->
        <div class="form-card">
          <div class="card-header"><h2>Inspection Information</h2></div>
          <div class="card-body">
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label required">Inspection Date</label>
                <input v-model="inspectionDate" type="date" class="form-input" required />
              </div>
              <div class="form-group">
                <label class="form-label required">Painting Date</label>
                <input v-model="paintingDate" type="date" class="form-input" required />
              </div>
              <div class="form-group">
                <label class="form-label">Oven Out Time</label>
                <input v-model="ovenOutTime" type="time" class="form-input" placeholder="HH:MM" />
              </div>
              <div class="form-group">
                <label class="form-label required">Color</label>
                <input v-model="color" type="text" class="form-input" placeholder="e.g., White" required />
              </div>
              <div class="form-group">
                <label class="form-label required">VIN No</label>
                <input v-model="vinNo" type="text" class="form-input" placeholder="e.g., 3/331" required />
              </div>
            </div>
          </div>
        </div>

        <!-- Vehicle Diagram -->
        <div class="form-card">
          <div class="card-header">
            <h2>Vehicle Diagram</h2>
            <button type="button" class="toggle-btn" @click="showDiagram = !showDiagram">
              <i :class="showDiagram ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"></i>
            </button>
          </div>
          <div v-show="showDiagram" class="card-body">
            <Vehicle3DViewer
              :vehicle-parts="vehicleParts"
              :defects="defects"
              @add-defect="addDefectToPart"
              @remove-defect="removeDefectFromPart"
              @update-defect="updateDefectOnPart"
            />
          </div>
        </div>

        <!-- Defects Table -->
        <div class="form-card">
          <div class="card-header">
            <h2>Inspection Data</h2>
            <button type="button" class="add-btn" @click="addDefect">
              <i class="fa-solid fa-plus"></i>
              Add Row
            </button>
          </div>
          <div class="card-body">
            <DefectsTable :defects="inspectionDefects" @remove-defect="removeDefect" />
            <div class="total-problems">
              <span class="total-label">TOTAL PROBLEMS:</span>
              <span class="total-value">{{ computedTotalProblems }}</span>
            </div>
          </div>
        </div>

        <!-- Approval -->
        <div class="form-card">
          <div class="card-header"><h2>Approval</h2></div>
          <div class="card-body">
            <div class="approval-grid">
              <div class="form-group">
                <label class="form-label">Checked By</label>
                <input v-model="checkedBy" type="text" class="form-input" placeholder="Name" />
              </div>
              <div class="form-group">
                <label class="form-label">Confirmed By</label>
                <input v-model="confirmedBy" type="text" class="form-input" placeholder="Name" />
              </div>
              <div class="form-group">
                <label class="form-label">Approved By</label>
                <input v-model="approvedBy" type="text" class="form-input" placeholder="Name" />
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="form-actions">
          <VButton variant="secondary" size="lg" @click="resetForm" :disabled="loading">
            <i class="fa-solid fa-rotate-right"></i>
            Reset Form
          </VButton>
          <VButton size="lg" @click="submitForm" :disabled="!isFormValid || loading">
            <i :class="loading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-save'"></i>
            {{ loading ? (isEditMode ? 'Updating...' : 'Saving...') : (isEditMode ? 'Update Inspection' : 'Save Inspection') }}
          </VButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped src="@/styles/pages/paint-inspection-form.css"></style>
