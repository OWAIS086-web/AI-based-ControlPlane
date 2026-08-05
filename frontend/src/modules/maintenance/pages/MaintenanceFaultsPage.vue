<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { usePaintDashboard } from '@/modules/paint-inspection/composables/usePaintDashboard'
import { paintInspectionService } from '@/services/paint-inspection.service'
import type { PaintInspection, InspectionDefect } from '@/types/paint-inspection'

const router     = useRouter()
const { toast }  = useToast()

const { loading, inspections, fetchDashboardData } = usePaintDashboard()

// ── Tab ─────────────────────────────────────────────────────────────
const activeTab = ref<'faults' | 'paint'>('faults')

// ── Fault Records (flattened defects from all inspections) ──────────
interface FaultRow extends InspectionDefect {
  inspection_date: string
  vin_no: string
  color: string
}

const faultPage    = ref(1)
const FAULT_PAGE   = 20
const faultFilter  = reactive({ name: '', vin_no: '' })

const allFaultRows = computed<FaultRow[]>(() =>
  inspections.value.flatMap(insp =>
    insp.defects.map(d => ({
      ...d,
      inspection_date: insp.inspection_date,
      vin_no: insp.vin_no,
      color: insp.color,
    }))
  ).filter(r => {
    if (faultFilter.name   && !r.name.toLowerCase().includes(faultFilter.name.toLowerCase()))     return false
    if (faultFilter.vin_no && !r.vin_no.toLowerCase().includes(faultFilter.vin_no.toLowerCase())) return false
    return true
  })
)

const faultTotalPages = computed(() => Math.max(1, Math.ceil(allFaultRows.value.length / FAULT_PAGE)))
const faultRows       = computed(() =>
  allFaultRows.value.slice((faultPage.value - 1) * FAULT_PAGE, faultPage.value * FAULT_PAGE)
)

function faultApply()  { faultPage.value = 1 }
function faultClear()  { faultFilter.name = ''; faultFilter.vin_no = ''; faultPage.value = 1 }

// ── Paint Inspections list (same source, inspection-level view) ──────
const piPage    = ref(1)
const PI_PAGE   = 20
const piFilter  = reactive({ vin_no: '', color: '' })

const filteredInspections = computed<PaintInspection[]>(() =>
  inspections.value.filter(i => {
    if (piFilter.vin_no && !i.vin_no.toLowerCase().includes(piFilter.vin_no.toLowerCase())) return false
    if (piFilter.color  && !i.color.toLowerCase().includes(piFilter.color.toLowerCase()))   return false
    return true
  })
)

const piTotalPages = computed(() => Math.max(1, Math.ceil(filteredInspections.value.length / PI_PAGE)))
const piRows       = computed(() =>
  filteredInspections.value.slice((piPage.value - 1) * PI_PAGE, piPage.value * PI_PAGE)
)

function piApply() { piPage.value = 1 }
function piClear() { piFilter.vin_no = ''; piFilter.color = ''; piPage.value = 1 }

async function deleteInspection(id: number) {
  if (!confirm('Delete this paint inspection? This cannot be undone.')) return
  try {
    await paintInspectionService.delete(id)
    toast('Inspection deleted', 'warning')
    fetchDashboardData()
  } catch (e: any) {
    toast(e.message, 'error')
  }
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="m-faults">

    <!-- Tab bar -->
    <div class="m-tabs">
      <button class="m-tab" :class="{ 'm-tab--active': activeTab === 'faults' }" @click="activeTab = 'faults'">
        <i class="fa-solid fa-bug"></i>
        Fault Records
        <span class="m-tab-count">{{ allFaultRows.length }}</span>
      </button>
      <button class="m-tab" :class="{ 'm-tab--active': activeTab === 'paint' }" @click="activeTab = 'paint'">
        <i class="fa-solid fa-spray-can-sparkles"></i>
        Paint Inspections
        <span class="m-tab-count">{{ inspections.length }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="m-loading">
      <i class="fa-solid fa-spinner fa-spin"></i> Loading…
    </div>

    <template v-else>

      <!-- ── FAULT RECORDS TAB ───────────────────────────────────── -->
      <template v-if="activeTab === 'faults'">

        <div class="m-page-header">
          <div class="m-page-header-text">
            <h1>Fault Records</h1>
            <p>{{ allFaultRows.length }} defect{{ allFaultRows.length !== 1 ? 's' : '' }} across {{ inspections.length }} inspection{{ inspections.length !== 1 ? 's' : '' }}</p>
          </div>
          <button class="m-btn m-btn-secondary" @click="fetchDashboardData">
            <i class="fa-solid fa-rotate-right"></i> Refresh
          </button>
        </div>

        <div class="m-filter-card">
          <div class="m-filter-group">
            <label>Defect Name</label>
            <input v-model="faultFilter.name" class="m-input" placeholder="e.g. Dust, Sag…" @keydown.enter="faultApply"/>
          </div>
          <div class="m-filter-group">
            <label>VIN No.</label>
            <input v-model="faultFilter.vin_no" class="m-input" placeholder="Search VIN…" @keydown.enter="faultApply"/>
          </div>
          <button class="m-btn m-btn-primary" @click="faultApply">
            <i class="fa-solid fa-filter"></i> Apply
          </button>
          <button class="m-btn m-btn-secondary" @click="faultClear">
            <i class="fa-solid fa-xmark"></i> Clear
          </button>
        </div>

        <div class="m-card">
          <div v-if="faultRows.length === 0" class="m-empty">
            <i class="fa-solid fa-bug" style="font-size:2rem;display:block;margin-bottom:0.75rem;color:#d1d5db;"></i>
            No fault records found.
            <br/>
            <button class="m-btn m-btn-primary" style="margin-top:1rem"
              @click="router.push({ name: 'paint-inspection-new' })">
              <i class="fa-solid fa-plus"></i> New Inspection
            </button>
          </div>
          <div v-else class="m-table-wrap">
            <table class="m-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Date</th>
                  <th>VIN</th>
                  <th>Color</th>
                  <th>Defect</th>
                  <th style="text-align:center">Total</th>
                  <th style="text-align:center">Repaired</th>
                  <th style="text-align:center">Let Go</th>
                  <th>Remarks</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in faultRows" :key="`${row.inspection_id}-${row.serial_no}`">
                  <td style="color:#9ca3af;font-size:0.8rem">
                    {{ (faultPage - 1) * FAULT_PAGE + idx + 1 }}
                  </td>
                  <td style="white-space:nowrap;font-size:0.8125rem">{{ fmtDate(row.inspection_date) }}</td>
                  <td style="font-weight:700;color:#1e40af">{{ row.vin_no }}</td>
                  <td>
                    <span class="m-badge" style="background:#eff6ff;color:#1e40af;border:1px solid #dbeafe">
                      {{ row.color }}
                    </span>
                  </td>
                  <td style="font-weight:600;color:#111827">{{ row.name }}</td>
                  <td style="text-align:center;font-weight:700">{{ row.total_qty ?? '—' }}</td>
                  <td style="text-align:center">
                    <span class="m-badge" style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0">
                      {{ row.repair_qty ?? 0 }}
                    </span>
                  </td>
                  <td style="text-align:center">
                    <span class="m-badge" style="background:#f5f3ff;color:#6b21a8;border:1px solid #e9d5ff">
                      {{ row.let_go_qty ?? 0 }}
                    </span>
                  </td>
                  <td style="color:#6b7280;font-size:0.8125rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                    {{ row.remarks || '—' }}
                  </td>
                  <td>
                    <button class="m-btn-icon" title="View inspection"
                      @click="router.push({ name: 'paint-inspection-view', params: { id: row.inspection_id } })">
                      <i class="fa-solid fa-eye"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="faultTotalPages > 1" class="m-pagination">
            <span class="m-pagination-info">
              Page {{ faultPage }} of {{ faultTotalPages }} ({{ allFaultRows.length }} total)
            </span>
            <div class="m-pagination-controls">
              <button class="m-btn m-btn-secondary m-btn-sm" :disabled="faultPage <= 1" @click="faultPage--">
                <i class="fa-solid fa-chevron-left"></i> Previous
              </button>
              <button class="m-btn m-btn-secondary m-btn-sm" :disabled="faultPage >= faultTotalPages" @click="faultPage++">
                Next <i class="fa-solid fa-chevron-right"></i>
              </button>
            </div>
          </div>
        </div>

      </template>

      <!-- ── PAINT INSPECTIONS TAB ──────────────────────────────── -->
      <template v-else>

        <div class="m-page-header">
          <div class="m-page-header-text">
            <h1>Paint Inspections</h1>
            <p>{{ inspections.length }} inspection{{ inspections.length !== 1 ? 's' : '' }} recorded</p>
          </div>
          <button class="m-btn m-btn-primary" @click="router.push({ name: 'paint-inspection-new' })">
            <i class="fa-solid fa-plus"></i> New Inspection
          </button>
        </div>

        <div class="m-filter-card">
          <div class="m-filter-group">
            <label>VIN No.</label>
            <input v-model="piFilter.vin_no" class="m-input" placeholder="Search VIN…" @keydown.enter="piApply"/>
          </div>
          <div class="m-filter-group">
            <label>Color</label>
            <input v-model="piFilter.color" class="m-input" placeholder="Search color…" @keydown.enter="piApply"/>
          </div>
          <button class="m-btn m-btn-primary" @click="piApply">
            <i class="fa-solid fa-filter"></i> Apply
          </button>
          <button class="m-btn m-btn-secondary" @click="piClear">
            <i class="fa-solid fa-xmark"></i> Clear
          </button>
        </div>

        <div class="m-card">
          <div v-if="piRows.length === 0" class="m-empty">
            <i class="fa-solid fa-spray-can-sparkles" style="font-size:2rem;display:block;margin-bottom:0.75rem;color:#d1d5db;"></i>
            No inspections found.
            <br/>
            <button class="m-btn m-btn-primary" style="margin-top:1rem"
              @click="router.push({ name: 'paint-inspection-new' })">
              <i class="fa-solid fa-plus"></i> New Inspection
            </button>
          </div>
          <div v-else class="m-table-wrap">
            <table class="m-table">
              <thead>
                <tr>
                  <th>Inspection Date</th>
                  <th>VIN No.</th>
                  <th>Color</th>
                  <th>Problems</th>
                  <th>Painting Date</th>
                  <th>Checked By</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="insp in piRows" :key="insp.id">
                  <td style="white-space:nowrap">{{ fmtDate(insp.inspection_date) }}</td>
                  <td style="font-weight:700;color:#1e40af">{{ insp.vin_no }}</td>
                  <td>
                    <span class="m-badge" style="background:#eff6ff;color:#1e40af;border:1px solid #dbeafe">
                      {{ insp.color }}
                    </span>
                  </td>
                  <td>
                    <span class="m-badge"
                      :style="insp.total_problems > 0
                        ? 'background:#fee2e2;color:#991b1b;border:1px solid #fecaca'
                        : 'background:#f3f4f6;color:#374151;border:1px solid #e5e7eb'">
                      {{ insp.total_problems }}
                    </span>
                  </td>
                  <td style="color:#6b7280;font-size:0.8125rem;white-space:nowrap">{{ fmtDate(insp.painting_date) }}</td>
                  <td style="color:#6b7280;font-size:0.8125rem">{{ insp.checked_by || '—' }}</td>
                  <td>
                    <div style="display:flex;gap:0.5rem">
                      <button class="m-btn-icon" title="View"
                        @click="router.push({ name: 'paint-inspection-view', params: { id: insp.id } })">
                        <i class="fa-solid fa-eye"></i>
                      </button>
                      <button class="m-btn-icon" title="Edit"
                        @click="router.push({ name: 'paint-inspection-edit', params: { id: insp.id } })">
                        <i class="fa-solid fa-pen"></i>
                      </button>
                      <button class="m-btn-icon danger" title="Delete"
                        @click="deleteInspection(insp.id)">
                        <i class="fa-solid fa-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="piTotalPages > 1" class="m-pagination">
            <span class="m-pagination-info">
              Page {{ piPage }} of {{ piTotalPages }} ({{ filteredInspections.length }} total)
            </span>
            <div class="m-pagination-controls">
              <button class="m-btn m-btn-secondary m-btn-sm" :disabled="piPage <= 1" @click="piPage--">
                <i class="fa-solid fa-chevron-left"></i> Previous
              </button>
              <button class="m-btn m-btn-secondary m-btn-sm" :disabled="piPage >= piTotalPages" @click="piPage++">
                Next <i class="fa-solid fa-chevron-right"></i>
              </button>
            </div>
          </div>
        </div>

      </template>

    </template>
  </div>
</template>

<style scoped src="@/styles/pages/maintenance-faults.css"></style>
<style scoped>
.m-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
}
.m-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}
.m-tab:hover { color: #374151; }
.m-tab--active { color: #1d4ed8; border-bottom-color: #1d4ed8; }
.m-tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  background: #f3f4f6;
  color: #6b7280;
}
.m-tab--active .m-tab-count { background: #dbeafe; color: #1e40af; }

@media (max-width: 900px) {
  .m-tab { padding: 12px 14px; font-size: 0.85rem; min-height: 48px; }
  .m-tab-count { display: none; } /* save space on portrait tablet */
}
</style>
