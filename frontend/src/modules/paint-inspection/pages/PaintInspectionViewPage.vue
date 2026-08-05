<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { paintInspectionService } from '@/services/paint-inspection.service'
import type { PaintInspection } from '@/types/paint-inspection'
import Vehicle3DViewer from '../components/Vehicle3DViewer.vue'
import VButton from '@/components/ui/VButton.vue'

const route = useRoute()
const router = useRouter()

const inspection = ref<PaintInspection | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const fetchInspection = async () => {
  const id = Number(route.params.id)
  if (isNaN(id)) { error.value = 'Invalid inspection ID'; return }
  loading.value = true
  error.value = null
  try {
    inspection.value = await paintInspectionService.getById(id)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load inspection'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string) =>
  new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

const formatNumber = (value: number | null) =>
  (value === null || value === undefined) ? '-' : Math.round(value).toString()

const handleEdit = () => router.push(`/maintenance/paint-inspection/edit/${inspection.value?.id}`)

const handleDelete = async () => {
  if (!inspection.value) return
  if (!confirm(`Are you sure you want to delete this inspection for VIN ${inspection.value.vin_no}?`)) return
  try {
    await paintInspectionService.delete(inspection.value.id)
    router.back()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to delete inspection'
  }
}

onMounted(fetchInspection)
</script>

<template>
  <div class="view-page">
    <div class="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div v-if="loading" class="loading-state">
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Loading inspection...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <i class="fa-solid fa-circle-exclamation"></i>
        <h3>Error Loading Inspection</h3>
        <p>{{ error }}</p>
        <VButton @click="router.back()">
          <i class="fa-solid fa-arrow-left"></i>
          Back to History
        </VButton>
      </div>

      <div v-else-if="inspection" class="inspection-content">
        <!-- Header -->
        <div class="page-header">
          <div class="header-content">
            <div class="header-title">
              <i class="fa-solid fa-file-lines"></i>
              <div>
                <h1>Paint Inspection Sheet</h1>
                <p class="subtitle">VIN: {{ inspection.vin_no }}</p>
              </div>
            </div>
            <div class="header-actions">
              <VButton variant="secondary" @click="router.back()">
                <i class="fa-solid fa-arrow-left"></i>
                Back
              </VButton>
              <VButton @click="handleEdit">
                <i class="fa-solid fa-edit"></i>
                Edit
              </VButton>
              <VButton variant="danger" @click="handleDelete">
                <i class="fa-solid fa-trash"></i>
                Delete
              </VButton>
            </div>
          </div>
        </div>

        <!-- Info Card -->
        <div class="info-card">
          <div class="card-header"><h2>Inspection Information</h2></div>
          <div class="card-body">
            <div class="info-grid">
              <div class="info-item">
                <label>Inspection Date</label>
                <div class="info-value">{{ formatDate(inspection.inspection_date) }}</div>
              </div>
              <div class="info-item">
                <label>Painting Date</label>
                <div class="info-value">{{ formatDate(inspection.painting_date) }}</div>
              </div>
              <div class="info-item">
                <label>Oven Out Time</label>
                <div class="info-value">{{ inspection.oven_out_time || '-' }}</div>
              </div>
              <div class="info-item">
                <label>Color</label>
                <div class="info-value"><span class="color-badge">{{ inspection.color }}</span></div>
              </div>
              <div class="info-item">
                <label>VIN Number</label>
                <div class="info-value vin-value">{{ inspection.vin_no }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Vehicle Diagram -->
        <div class="info-card">
          <div class="card-header"><h2>Vehicle Diagram</h2></div>
          <div class="card-body">
            <Vehicle3DViewer
              :vehicle-parts="inspection.vehicle_parts"
              :defects="inspection.defects"
              :readonly="true"
            />
          </div>
        </div>

        <!-- Defects Table -->
        <div class="info-card">
          <div class="card-header"><h2>Inspection Data</h2></div>
          <div class="card-body">
            <div class="table-container">
              <table class="defects-table">
                <thead>
                  <tr>
                    <th class="col-sno">S.NO</th>
                    <th class="col-name">NAME</th>
                    <th class="col-qty">TOTAL QTY</th>
                    <th class="col-qty">LET GO QTY</th>
                    <th class="col-qty">REPAIR QTY</th>
                    <th class="col-remarks">REMARKS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="defect in inspection.defects" :key="defect.id">
                    <td class="col-sno"><span class="serial-badge">{{ defect.serial_no }}</span></td>
                    <td class="col-name"><strong>{{ defect.name }}</strong></td>
                    <td class="col-qty">{{ formatNumber(defect.total_qty) }}</td>
                    <td class="col-qty">{{ formatNumber(defect.let_go_qty) }}</td>
                    <td class="col-qty">{{ formatNumber(defect.repair_qty) }}</td>
                    <td class="col-remarks">{{ defect.remarks || '-' }}</td>
                  </tr>
                  <tr v-if="inspection.defects.length === 0">
                    <td colspan="6" class="empty-cell">No defects recorded</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="total-problems">
              <span class="total-label">TOTAL PROBLEMS:</span>
              <span class="total-value">{{ inspection.total_problems }}</span>
            </div>
          </div>
        </div>

        <!-- Approval -->
        <div class="info-card">
          <div class="card-header"><h2>Approval</h2></div>
          <div class="card-body">
            <div class="approval-grid">
              <div class="info-item">
                <label>Checked By</label>
                <div class="info-value">{{ inspection.checked_by || '-' }}</div>
              </div>
              <div class="info-item">
                <label>Confirmed By</label>
                <div class="info-value">{{ inspection.confirmed_by || '-' }}</div>
              </div>
              <div class="info-item">
                <label>Approved By</label>
                <div class="info-value">{{ inspection.approved_by || '-' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Metadata -->
        <div class="info-card">
          <div class="metadata">
            <p>Created: {{ formatDate(inspection.created_at) }}</p>
            <p>Last Updated: {{ formatDate(inspection.updated_at) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped src="@/styles/pages/paint-inspection-view.css"></style>
