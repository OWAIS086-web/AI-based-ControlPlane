<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { paintInspectionService } from '@/services/paint-inspection.service'
import type { PaintInspection, PaintInspectionFilter } from '@/types/paint-inspection'
import VButton from '@/components/ui/VButton.vue'

const router = useRouter()

const inspections = ref<PaintInspection[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)
const totalPages = ref(0)
const total = ref(0)

const filters = ref<Omit<PaintInspectionFilter, 'page' | 'page_size'>>({
  vin_no: '',
  color: '',
  inspection_date_from: '',
  inspection_date_to: '',
  checked_by: '',
})

const hasFilters = computed(() => Object.values(filters.value).some((v) => v !== ''))

const fetchInspections = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await paintInspectionService.getList({
      page: currentPage.value,
      page_size: pageSize.value,
      ...filters.value,
    })
    inspections.value = response.items
    total.value = response.total
    totalPages.value = response.total_pages
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load inspections'
  } finally {
    loading.value = false
  }
}

const clearFilters = () => {
  filters.value = { vin_no: '', color: '', inspection_date_from: '', inspection_date_to: '', checked_by: '' }
  currentPage.value = 1
  fetchInspections()
}

const applyFilters = () => { currentPage.value = 1; fetchInspections() }
const goToPage = (page: number) => { currentPage.value = page; fetchInspections() }

const viewInspection = (id: number) => router.push(`/maintenance/paint-inspection/view/${id}`)
const editInspection = (id: number) => router.push(`/maintenance/paint-inspection/edit/${id}`)

const deleteInspection = async (inspection: PaintInspection) => {
  if (!confirm(`Are you sure you want to delete inspection for VIN ${inspection.vin_no}?`)) return
  try {
    await paintInspectionService.delete(inspection.id)
    fetchInspections()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to delete inspection'
  }
}

const formatDate = (dateString: string) =>
  new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })

const formatNumber = (value: number) => Math.round(value).toString()

onMounted(fetchInspections)
</script>

<template>
  <div class="history-page">
    <div class="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Header -->
      <div class="page-header mb-6">
        <div class="header-content">
          <div class="header-title">
            <i class="fa-solid fa-history"></i>
            <h1>Paint Inspection History</h1>
          </div>
          <div class="header-actions">
            <VButton @click="router.push('/maintenance/paint-inspection/new')">
              <i class="fa-solid fa-plus"></i>
              New Inspection
            </VButton>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-card">
        <div class="filters-header">
          <h2>Filters</h2>
          <button v-if="hasFilters" @click="clearFilters" class="clear-btn">
            <i class="fa-solid fa-times"></i>
            Clear Filters
          </button>
        </div>
        <div class="filters-grid">
          <div class="filter-group">
            <label>VIN Number</label>
            <input v-model="filters.vin_no" type="text" placeholder="Search by VIN" class="filter-input" @keyup.enter="applyFilters" />
          </div>
          <div class="filter-group">
            <label>Color</label>
            <input v-model="filters.color" type="text" placeholder="Search by color" class="filter-input" @keyup.enter="applyFilters" />
          </div>
          <div class="filter-group">
            <label>Inspection Date From</label>
            <input v-model="filters.inspection_date_from" type="date" class="filter-input" />
          </div>
          <div class="filter-group">
            <label>Inspection Date To</label>
            <input v-model="filters.inspection_date_to" type="date" class="filter-input" />
          </div>
          <div class="filter-group">
            <label>Checked By</label>
            <input v-model="filters.checked_by" type="text" placeholder="Search by checker" class="filter-input" @keyup.enter="applyFilters" />
          </div>
          <div class="filter-group filter-actions">
            <VButton @click="applyFilters" :disabled="loading">
              <i class="fa-solid fa-search"></i>
              Search
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
        <p>Loading inspections...</p>
      </div>

      <div v-else-if="inspections.length > 0" class="table-card">
        <div class="table-container">
          <table class="inspections-table">
            <thead>
              <tr>
                <th>VIN Number</th>
                <th>Color</th>
                <th>Inspection Date</th>
                <th>Painting Date</th>
                <th>Oven Out Time</th>
                <th>Total Defects</th>
                <th>Checked By</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inspection in inspections" :key="inspection.id" class="inspection-row">
                <td class="vin-cell"><strong>{{ inspection.vin_no }}</strong></td>
                <td><span class="color-badge">{{ inspection.color }}</span></td>
                <td>{{ formatDate(inspection.inspection_date) }}</td>
                <td>{{ formatDate(inspection.painting_date) }}</td>
                <td>{{ inspection.oven_out_time || '-' }}</td>
                <td>
                  <span class="defect-badge" :class="{ 'has-defects': inspection.total_problems > 0 }">
                    {{ formatNumber(inspection.total_problems) }}
                  </span>
                </td>
                <td>{{ inspection.checked_by || '-' }}</td>
                <td class="actions-cell">
                  <button @click="viewInspection(inspection.id)" class="action-btn view-btn" title="View">
                    <i class="fa-solid fa-eye"></i>
                  </button>
                  <button @click="editInspection(inspection.id)" class="action-btn edit-btn" title="Edit">
                    <i class="fa-solid fa-edit"></i>
                  </button>
                  <button @click="deleteInspection(inspection)" class="action-btn delete-btn" title="Delete">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="totalPages > 1" class="pagination">
          <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1" class="pagination-btn">
            <i class="fa-solid fa-chevron-left"></i> Previous
          </button>
          <div class="pagination-info">Page {{ currentPage }} of {{ totalPages }} ({{ total }} total)</div>
          <button @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages" class="pagination-btn">
            Next <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>

      <div v-else class="empty-state">
        <i class="fa-solid fa-inbox"></i>
        <h3>No Inspections Found</h3>
        <p v-if="hasFilters">Try adjusting your filters or clear them to see all inspections.</p>
        <p v-else>No paint inspections have been created yet.</p>
        <VButton @click="router.push('/maintenance/paint-inspection/new')">
          <i class="fa-solid fa-plus"></i>
          Create First Inspection
        </VButton>
      </div>
    </div>
  </div>
</template>

<style scoped src="@/styles/pages/paint-inspection-history.css"></style>
