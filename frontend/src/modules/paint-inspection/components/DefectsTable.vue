<script setup lang="ts">
import type { InspectionDefect } from '@/types/paint-inspection'

interface Props {
  defects: Omit<InspectionDefect, 'id' | 'inspection_id' | 'created_at' | 'updated_at'>[]
}

defineProps<Props>()
const emit = defineEmits<{ removeDefect: [index: number] }>()

const handleRemove = (index: number) => {
  if (confirm('Are you sure you want to remove this defect?')) {
    emit('removeDefect', index)
  }
}
</script>

<template>
  <div class="defects-table-container">
    <table class="defects-table">
      <thead>
        <tr>
          <th class="col-sno">S.NO</th>
          <th class="col-name">NAME</th>
          <th class="col-qty">Total Qty</th>
          <th class="col-qty">Let Go Qty</th>
          <th class="col-qty">Repair Qty</th>
          <th class="col-remarks">REMARKS</th>
          <th class="col-actions">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(defect, index) in defects" :key="index" class="defect-row">
          <td class="col-sno">
            <span class="serial-badge">{{ defect.serial_no }}</span>
          </td>
          <td class="col-name">
            <input v-model="defect.name" type="text" class="table-input" placeholder="Defect name" />
          </td>
          <td class="col-qty">
            <input
              v-model.number="defect.total_qty"
              type="number"
              class="table-input text-center"
              min="0"
              placeholder="0"
              @input="(e) => { const val = parseInt((e.target as HTMLInputElement).value); defect.total_qty = isNaN(val) ? null : val }"
            />
          </td>
          <td class="col-qty">
            <input
              v-model.number="defect.let_go_qty"
              type="number"
              class="table-input text-center"
              min="0"
              placeholder="0"
              @input="(e) => { const val = parseInt((e.target as HTMLInputElement).value); defect.let_go_qty = isNaN(val) ? null : val }"
            />
          </td>
          <td class="col-qty">
            <input
              v-model.number="defect.repair_qty"
              type="number"
              class="table-input text-center"
              min="0"
              placeholder="0"
              @input="(e) => { const val = parseInt((e.target as HTMLInputElement).value); defect.repair_qty = isNaN(val) ? null : val }"
            />
          </td>
          <td class="col-remarks">
            <input v-model="defect.remarks" type="text" class="table-input" placeholder="Additional notes" />
          </td>
          <td class="col-actions">
            <button type="button" class="remove-btn" @click="handleRemove(index)" title="Remove defect">
              <i class="fa-solid fa-trash"></i>
            </button>
          </td>
        </tr>
        <tr v-if="defects.length === 0" class="empty-row">
          <td colspan="7" class="empty-message">
            <i class="fa-solid fa-inbox"></i>
            <p>No defects added yet. Click "Add Row" to add a defect.</p>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.defects-table-container {
  width: 100%;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.defects-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }

.defects-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.defects-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  white-space: nowrap;
}

.defects-table th.col-qty { text-align: center; }

.defects-table td {
  padding: 8px 16px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.defect-row:hover { background: #f9fafb; }

.col-sno { width: 80px; text-align: center; }
.col-name { min-width: 180px; width: 25%; }
.col-qty { width: 120px; text-align: center; }
.col-remarks { min-width: 200px; width: 30%; }
.col-actions { width: 100px; text-align: center; }

.serial-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.875rem;
}

.table-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  background: white;
  color: #111827;
  transition: all 0.2s;
  box-sizing: border-box;
}

.table-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.table-input.text-center { text-align: center; }

.table-input[type="number"]::-webkit-inner-spin-button,
.table-input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.table-input[type="number"] { -moz-appearance: textfield; }

.remove-btn {
  padding: 8px 12px;
  background: transparent;
  border: 1px solid #fca5a5;
  color: #dc2626;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-btn:hover { background: #fee2e2; border-color: #dc2626; color: #991b1b; }

.empty-row { background: #f9fafb; }

.empty-message {
  padding: 48px 24px !important;
  text-align: center;
  color: #9ca3af;
}

.empty-message i {
  font-size: 2rem;
  margin-bottom: 12px;
  display: block;
  opacity: 0.5;
}

.empty-message p { margin: 0; font-size: 0.875rem; }

@media (max-width: 768px) {
  .defects-table { min-width: 800px; }
}
</style>
