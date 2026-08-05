<script setup lang="ts">
import { ref, computed } from 'vue'

interface ShapeChange {
  name: string
  type: 'added' | 'modified' | 'deleted'
  oldText?: string
  newText?: string
}

interface CellDiff {
  cell: string
  old_value: string
  new_value: string
}

interface CellData {
  coord: string
  value: string
  colSpan?: number
  rowSpan?: number
  width?: number
  height?: number
  changed?: boolean
}

interface RowData {
  row: number
  height?: number
  cells: CellData[]
}

export interface DiffData {
  sheetName?: string
  rows?: RowData[]
  changedCells?: string[]
  cellDiffs?: CellDiff[]
  shapeChanges?: ShapeChange[]
}

const props = defineProps<{ diffData: DiffData }>()

const sheetName      = computed(() => props.diffData.sheetName || 'Sheet')
const rows           = computed(() => props.diffData.rows || [])
const shapeChanges   = computed(() => props.diffData.shapeChanges || [])
const cellDiffsData  = computed(() => props.diffData.cellDiffs || [])
const changedCells   = computed(() => props.diffData.changedCells || [])
const addedShapes    = computed(() => shapeChanges.value.filter(s => s.type === 'added'))
const modifiedShapes = computed(() => shapeChanges.value.filter(s => s.type === 'modified'))
const hasChanges     = computed(() =>
  changedCells.value.length > 0 || shapeChanges.value.length > 0 || cellDiffsData.value.length > 0
)

const oldValues = computed(() => {
  const m: Record<string, string> = {}
  for (const d of cellDiffsData.value) m[d.cell] = d.old_value
  return m
})

const tableMinWidth = computed(() => {
  if (!rows.value.length || !rows.value[0].cells.length) return 800
  return rows.value[0].cells.reduce((sum, c) => sum + (c.width || 60), 0)
})

const selectedCell = ref<CellData | null>(null)

function selectCell(cell: CellData) {
  selectedCell.value = selectedCell.value?.coord === cell.coord ? null : cell
}

function getOldValue(coord: string) {
  return oldValues.value[coord] ?? '—'
}

function formatValue(val: string | null | undefined) {
  if (!val) return ''
  return String(val).replace(/\n/g, '<br>')
}
</script>

<template>
  <div class="excel-diff-viewer">
    <!-- Header -->
    <div class="diff-header">
      <div class="diff-header-left">
        <div class="sheet-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>
          </svg>
        </div>
        <div>
          <div class="sheet-name">{{ sheetName }}</div>
          <div class="diff-subtitle">Latest version diff</div>
        </div>
      </div>
      <div class="diff-badges">
        <span class="badge badge-modified" v-if="cellDiffsData.length">
          {{ cellDiffsData.length }} cell{{ cellDiffsData.length > 1 ? 's' : '' }} changed
        </span>
        <span class="badge badge-added" v-if="addedShapes.length">
          {{ addedShapes.length }} shape{{ addedShapes.length > 1 ? 's' : '' }} added
        </span>
        <span class="badge badge-modified" v-if="modifiedShapes.length">
          {{ modifiedShapes.length }} shape{{ modifiedShapes.length > 1 ? 's' : '' }} modified
        </span>
        <span class="badge badge-clean" v-if="!hasChanges">No changes</span>
      </div>
    </div>

    <!-- Shape changes panel -->
    <div class="shape-changes-panel" v-if="shapeChanges.length">
      <div class="panel-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
        </svg>
        Diagram / Shape Changes
      </div>
      <div class="shape-change-list">
        <div v-for="s in shapeChanges" :key="s.name" class="shape-change-item" :class="`shape-${s.type}`">
          <span class="shape-badge" :class="`type-${s.type}`">{{ s.type }}</span>
          <span class="shape-name">{{ s.name }}</span>
          <div class="shape-diff" v-if="s.type === 'modified'">
            <span class="old-val">{{ s.oldText }}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            <span class="new-val">{{ s.newText }}</span>
          </div>
          <div class="shape-diff" v-else-if="s.type === 'added'">
            <span class="new-val">{{ s.newText }}</span>
          </div>
          <div class="shape-diff" v-else-if="s.type === 'deleted'">
            <span class="old-val">{{ s.oldText }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cell changes list (when no full row data from API yet) -->
    <div class="cell-changes-panel" v-if="!rows.length && cellDiffsData.length">
      <div class="panel-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M3 9h18M3 15h18"/>
        </svg>
        Cell Changes
      </div>
      <div class="cell-change-list">
        <div v-for="d in cellDiffsData" :key="d.cell" class="cell-change-item">
          <span class="cell-coord-chip">{{ d.cell }}</span>
          <div class="cell-change-diff">
            <span class="old-val" v-if="d.old_value">{{ d.old_value }}</span>
            <svg v-if="d.old_value || d.new_value" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            <span class="new-val" v-if="d.new_value">{{ d.new_value }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- No changes empty state -->
    <div class="empty-state" v-if="!hasChanges && !rows.length">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="empty-icon">
        <path d="M9 12l2 2 4-4"/><rect x="3" y="3" width="18" height="18" rx="2"/>
      </svg>
      <div class="empty-text">No changes in this version</div>
    </div>

    <!-- Full spreadsheet table (when rows data is available) -->
    <div class="table-scroll-wrapper" v-if="rows.length" ref="tableWrapper">
      <div class="table-container">
        <table class="excel-table" :style="{ minWidth: tableMinWidth + 'px' }">
          <tbody>
            <template v-for="row in rows" :key="row.row">
              <tr v-if="row.cells.length > 0" :style="{ height: (row.height || 20) + 'px' }">
                <td
                  v-for="cell in row.cells"
                  :key="cell.coord"
                  :colspan="cell.colSpan || 1"
                  :rowspan="cell.rowSpan || 1"
                  :style="{ width: (cell.width || 60) + 'px', height: (cell.height || 20) + 'px' }"
                  :class="['excel-cell', cell.changed ? 'cell-changed' : '', (cell.rowSpan! > 1 || cell.colSpan! > 1) ? 'merged-cell' : '']"
                  @click="cell.changed && selectCell(cell)"
                >
                  <div class="cell-inner" :title="cell.value">
                    <span v-if="cell.changed" class="change-indicator" title="Changed">●</span>
                    <span class="cell-text" v-html="formatValue(cell.value)"></span>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Cell detail popover -->
    <transition name="slide-up">
      <div class="cell-detail" v-if="selectedCell">
        <div class="cell-detail-header">
          <span class="cell-coord-badge">{{ selectedCell.coord }}</span>
          <span class="change-type-label">Modified</span>
          <button class="close-btn" @click="selectedCell = null">✕</button>
        </div>
        <div class="cell-diff-content">
          <div class="diff-side old-side">
            <div class="diff-label">Before</div>
            <div class="diff-value">{{ getOldValue(selectedCell.coord) }}</div>
          </div>
          <div class="diff-arrow">→</div>
          <div class="diff-side new-side">
            <div class="diff-label">After</div>
            <div class="diff-value">{{ selectedCell.value }}</div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.excel-diff-viewer {
  --green-bg: #d1fae5; --green-border: #34d399; --green-text: #065f46; --green-dot: #10b981;
  --red-bg: #fee2e2; --red-text: #991b1b;
  --yellow-bg: #fef9c3; --yellow-text: #713f12;
  --gray-50: #f9fafb; --gray-100: #f3f4f6; --gray-200: #e5e7eb;
  --gray-400: #9ca3af; --gray-600: #4b5563; --gray-700: #374151; --gray-900: #111827;
  --cell-border: #d1d5db;
  --font-ui: 'DM Sans', 'Segoe UI', sans-serif;
  --font-cell: 'DM Mono', 'Cascadia Code', 'Consolas', monospace;
  font-family: var(--font-ui);
  background: var(--gray-50);
  border-right: 1px solid var(--gray-200);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.diff-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: white; border-bottom: 1px solid var(--gray-200);
  gap: 12px; flex-wrap: wrap; flex-shrink: 0;
}
.diff-header-left { display: flex; align-items: center; gap: 10px; }
.sheet-icon {
  width: 32px; height: 32px; background: #ecfdf5; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: var(--green-dot); flex-shrink: 0;
}
.sheet-name { font-size: 13px; font-weight: 600; color: var(--gray-900); }
.diff-subtitle { font-size: 11px; color: var(--gray-400); margin-top: 1px; }
.diff-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.badge { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 99px; }
.badge-modified { background: var(--yellow-bg); color: var(--yellow-text); }
.badge-added    { background: var(--green-bg);  color: var(--green-text); }
.badge-deleted  { background: var(--red-bg);    color: var(--red-text); }
.badge-clean    { background: var(--gray-100);  color: var(--gray-600); }

/* Shape changes */
.shape-changes-panel, .cell-changes-panel {
  background: white; border-bottom: 1px solid var(--gray-200);
  padding: 10px 16px; flex-shrink: 0;
}
.panel-title {
  font-size: 10px; font-weight: 700; color: var(--gray-600); text-transform: uppercase;
  letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;
}
.shape-change-list, .cell-change-list { display: flex; flex-direction: column; gap: 5px; }
.shape-change-item, .cell-change-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  border-radius: 6px; background: var(--gray-50); border: 1px solid var(--gray-200);
  font-size: 12px; flex-wrap: wrap;
}
.shape-badge {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  padding: 2px 6px; border-radius: 4px; flex-shrink: 0;
}
.type-added    { background: var(--green-bg);  color: var(--green-text); }
.type-modified { background: var(--yellow-bg); color: var(--yellow-text); }
.type-deleted  { background: var(--red-bg);    color: var(--red-text); }
.shape-name { font-weight: 500; color: var(--gray-700); flex-shrink: 0; }
.shape-diff, .cell-change-diff {
  display: flex; align-items: center; gap: 6px;
  font-family: var(--font-cell); font-size: 11px; flex-wrap: wrap;
}
.cell-coord-chip {
  font-family: var(--font-cell); font-size: 11px; font-weight: 700;
  background: var(--gray-900); color: white; padding: 2px 7px; border-radius: 4px; flex-shrink: 0;
}
.old-val {
  background: var(--red-bg); color: var(--red-text); padding: 1px 6px;
  border-radius: 4px; text-decoration: line-through; opacity: 0.85;
}
.new-val {
  background: var(--green-bg); color: var(--green-text); padding: 1px 6px;
  border-radius: 4px; font-weight: 600;
}

/* Empty state */
.empty-state {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 10px; padding: 40px;
}
.empty-icon { color: var(--gray-400); }
.empty-text { font-size: 13px; color: var(--gray-400); font-weight: 500; }

/* Table */
.table-scroll-wrapper {
  flex: 1; overflow: auto; background: white;
  scrollbar-width: thin; scrollbar-color: var(--gray-200) transparent;
}
.table-scroll-wrapper::-webkit-scrollbar { width: 6px; height: 6px; }
.table-scroll-wrapper::-webkit-scrollbar-thumb { background: var(--gray-200); border-radius: 99px; }
.excel-table { border-collapse: collapse; table-layout: fixed; font-size: 10px; font-family: var(--font-cell); }
.excel-cell {
  border: 1px solid var(--cell-border); padding: 0; vertical-align: top;
  overflow: hidden; position: relative; background: white;
}
.cell-inner {
  padding: 3px 5px; height: 100%; overflow: hidden;
  display: flex; align-items: flex-start; gap: 3px;
}
.cell-text { font-size: 9.5px; color: var(--gray-700); line-height: 1.35; white-space: pre-wrap; word-break: break-word; }
.merged-cell { background: var(--gray-50); }
.cell-changed {
  background: var(--green-bg) !important; border: 1.5px solid var(--green-border) !important;
  cursor: pointer; animation: highlight-pulse 1.5s ease-out;
}
.cell-changed:hover { background: #a7f3d0 !important; }
.cell-changed .cell-text { color: var(--green-text); font-weight: 600; }
@keyframes highlight-pulse {
  0%   { background: #6ee7b7; box-shadow: 0 0 0 3px #6ee7b7; }
  100% { background: var(--green-bg); box-shadow: none; }
}
.change-indicator { color: var(--green-dot); font-size: 7px; flex-shrink: 0; animation: blink 2s ease-in-out 3; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

/* Cell detail popover */
.cell-detail {
  flex-shrink: 0; background: white; border-top: 2px solid var(--green-border);
  padding: 12px 16px; box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
}
.cell-detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.cell-coord-badge {
  font-family: var(--font-cell); font-size: 12px; font-weight: 700;
  background: var(--gray-900); color: white; padding: 2px 8px; border-radius: 5px;
}
.change-type-label {
  font-size: 11px; font-weight: 600; color: var(--yellow-text);
  background: var(--yellow-bg); padding: 2px 8px; border-radius: 5px;
}
.close-btn {
  margin-left: auto; background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--gray-400); padding: 2px 6px; border-radius: 4px; transition: all 0.15s;
}
.close-btn:hover { background: var(--gray-100); color: var(--gray-700); }
.cell-diff-content { display: flex; align-items: stretch; gap: 12px; }
.diff-side { flex: 1; padding: 10px 13px; border-radius: 7px; }
.old-side { background: var(--red-bg); }
.new-side { background: var(--green-bg); }
.diff-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 4px; opacity: 0.7;
}
.old-side .diff-label { color: var(--red-text); }
.new-side .diff-label { color: var(--green-text); }
.diff-value { font-family: var(--font-cell); font-size: 12px; font-weight: 500; white-space: pre-wrap; line-height: 1.5; }
.old-side .diff-value { color: var(--red-text); text-decoration: line-through; opacity: 0.85; }
.new-side .diff-value { color: var(--green-text); font-weight: 700; }
.diff-arrow { display: flex; align-items: center; font-size: 18px; color: var(--gray-400); flex-shrink: 0; }

/* Transitions */
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(10px); }
</style>
