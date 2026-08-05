<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { UploadCloud, X, Plus, RotateCcw, Folder, CheckSquare, Square, AlertCircle, Clock, CheckCircle2, XCircle } from 'lucide-vue-next'
import { useUploadsStore } from '@/stores/uploads'
import { useStationsStore } from '@/stores/stations'
import { useToast } from '@/composables/useToast'
import AppButton from '@/components/ui/AppButton.vue'
import FileRow from './FileRow.vue'

const props = defineProps<{
  open: boolean
  lineId: string
  stationId: string
  carModelId: string
}>()

const emit = defineEmits<{ close: [] }>()

const store     = useUploadsStore()
const stStore   = useStationsStore()
const { toast } = useToast()

// ── Refresh stations after successful uploads ──────────────────────────────────
const successCount = computed(() =>
  store.queue.filter(e => e.status === 'created' || e.status === 'matched').length,
)

let refreshTimer: ReturnType<typeof setTimeout> | null = null

watch(successCount, (next, prev) => {
  if (next <= prev) return
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => {
    if (props.lineId) stStore.fetchStations(props.lineId)
  }, 600)
})

// ── Panel resize ──────────────────────────────────────────────────────────────
const MIN_W = 320
const MAX_W = 640
const STORAGE_KEY = 'cp_upload_panel_width'

const panelWidth = ref(
  Math.max(MIN_W, Math.min(MAX_W, parseInt(localStorage.getItem(STORAGE_KEY) ?? '420'))),
)

let resizeStartX = 0
let resizeStartW = 0

function startResize(e: MouseEvent) {
  e.preventDefault()
  resizeStartX = e.clientX
  resizeStartW = panelWidth.value
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeUp)
  document.body.style.userSelect = 'none'
  document.body.style.cursor     = 'col-resize'
}

function onResizeMove(e: MouseEvent) {
  const delta = resizeStartX - e.clientX
  panelWidth.value = Math.max(MIN_W, Math.min(MAX_W, resizeStartW + delta))
}

function onResizeUp() {
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeUp)
  document.body.style.userSelect = ''
  document.body.style.cursor     = ''
  localStorage.setItem(STORAGE_KEY, String(panelWidth.value))
}

// ── Drag & drop ───────────────────────────────────────────────────────────────
const isDragging = ref(false)
let dragTimer: ReturnType<typeof setTimeout> | null = null

function handleGlobalDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('Files')) return
  e.preventDefault()
  isDragging.value = true
  if (dragTimer) clearTimeout(dragTimer)
  dragTimer = setTimeout(() => { isDragging.value = false }, 200)
}

function handleGlobalDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  if (dragTimer) { clearTimeout(dragTimer); dragTimer = null }
  if (e.dataTransfer?.files.length) handleFiles(e.dataTransfer.files)
}

onMounted(() => {
  document.addEventListener('dragover', handleGlobalDragOver)
  document.addEventListener('drop', handleGlobalDrop)
})

onUnmounted(() => {
  document.removeEventListener('dragover', handleGlobalDragOver)
  document.removeEventListener('drop', handleGlobalDrop)
  if (dragTimer) clearTimeout(dragTimer)
  onResizeUp()
})

// ── File handling ─────────────────────────────────────────────────────────────
const fileInput       = ref<HTMLInputElement | null>(null)
const folderInput     = ref<HTMLInputElement | null>(null)

function triggerFileInput()   { fileInput.value?.click() }
function triggerFolderInput() { folderInput.value?.click() }

function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) {
    handleFiles(input.files)
    input.value = ''
  }
}

// ── Folder upload modal ───────────────────────────────────────────────────────
const ACCEPTED_EXTS = ['.xlsx', '.xls', '.csv']

interface FolderFile {
  file: File
  selected: boolean
  queueStatus: 'new' | 'pending' | 'uploading' | 'done' | 'error'
}

const showFolderModal  = ref(false)
const folderName       = ref('')
const folderFiles      = ref<FolderFile[]>([])

function getQueueStatus(name: string): FolderFile['queueStatus'] {
  const entry = store.queue.find(e => e.file.name === name)
  if (!entry) return 'new'
  if (entry.status === 'created' || entry.status === 'matched') return 'done'
  if (entry.status === 'error') return 'error'
  if (entry.status === 'uploading') return 'uploading'
  return 'pending'
}

function onFolderInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const arr = Array.from(input.files).filter(f =>
    ACCEPTED_EXTS.some(ext => f.name.toLowerCase().endsWith(ext))
  )
  input.value = ''
  if (!arr.length) { toast('No supported files found in folder', 'warning'); return }

  // derive folder name from first file's path
  const parts = (arr[0] as File & { webkitRelativePath?: string }).webkitRelativePath?.split('/') ?? []
  folderName.value  = parts[0] ?? 'Folder'
  folderFiles.value = arr.map(f => ({ file: f, selected: getQueueStatus(f.name) === 'new', queueStatus: getQueueStatus(f.name) }))
  showFolderModal.value = true
}

const folderSelectedCount = computed(() => folderFiles.value.filter(f => f.selected).length)
const folderNewCount      = computed(() => folderFiles.value.filter(f => f.queueStatus === 'new').length)

function selectAllNew() {
  folderFiles.value = folderFiles.value.map(f => ({ ...f, selected: f.queueStatus === 'new' }))
}
function toggleAll(val: boolean) {
  folderFiles.value = folderFiles.value.map(f => ({ ...f, selected: val }))
}

function submitFolderUpload() {
  if (!props.stationId || !props.carModelId) { toast('Select a station and car model first', 'error'); return }
  const selected = folderFiles.value.filter(f => f.selected).map(f => f.file)
  if (!selected.length) { toast('No files selected', 'warning'); return }
  // go through normal handleFiles so dupe modal triggers if needed
  handleFiles(selected)
  showFolderModal.value = false
}

// ── Dupe confirmation modal ───────────────────────────────────────────────────
const showDupeModal   = ref(false)
const dupeModalFiles  = ref<File[]>([])
const dupeNames       = ref<string[]>([])
let dupeCtx: { lineId: string; stationId: string; carModelId: string } | null = null

function handleFiles(files: FileList | File[]) {
  if (!props.stationId || !props.carModelId) {
    toast('Select a station and car model first', 'error')
    return
  }
  const arr  = Array.from(files)
  const names = arr
    .filter(f => store.queue.some(e => e.file.name === f.name))
    .map(f => f.name)

  if (names.length > 0) {
    dupeModalFiles.value = arr
    dupeNames.value      = names
    dupeCtx              = { lineId: props.lineId, stationId: props.stationId, carModelId: props.carModelId }
    showDupeModal.value  = true
    return
  }
  store.appendToQueue(arr, props.lineId, props.stationId, props.carModelId)
}

function confirmSkipAll() {
  if (!dupeCtx) return
  const fresh = dupeModalFiles.value.filter(f => !dupeNames.value.includes(f.name))
  if (fresh.length) store.appendToQueue(fresh, dupeCtx.lineId, dupeCtx.stationId, dupeCtx.carModelId)
  showDupeModal.value = false
}

function confirmUploadAll() {
  if (!dupeCtx) return
  store.appendToQueue(dupeModalFiles.value, dupeCtx.lineId, dupeCtx.stationId, dupeCtx.carModelId, true)
  showDupeModal.value = false
}

// ── Cancel remaining ──────────────────────────────────────────────────────────
const hasActive       = computed(() => store.queue.some(e => e.status === 'uploading' || e.status === 'pending'))
const uploadingCount  = computed(() => store.queue.filter(e => e.status === 'uploading').length)

function handleCancelRemaining() {
  if (uploadingCount.value > 3) {
    if (!window.confirm(`Cancel ${uploadingCount.value} active uploads and remove all pending files?`)) return
  }
  store.cancelRemaining()
}

// ── Header summary & progress ─────────────────────────────────────────────────
const summaryLine = computed(() => {
  const parts: string[] = []
  if (store.doneCount > 0)    parts.push(`${store.doneCount} done`)
  if (store.activeCount > 0)  parts.push(`${store.activeCount} uploading`)
  if (store.errorCount > 0)   parts.push(`${store.errorCount} failed`)
  if (store.pendingCount > 0) parts.push(`${store.pendingCount} pending`)
  return parts.join(' · ')
})

const overallPct = computed(() => {
  const total = store.totalCount
  return total === 0 ? 0 : Math.round((store.doneCount / total) * 100)
})
</script>

<template>
  <!-- Always in DOM so global drag listeners stay registered -->
  <Teleport to="body">
    <Transition name="upload-panel">
      <div
        v-show="open"
        class="fixed inset-y-0 right-0 z-[60] flex"
        :style="{ width: panelWidth + 'px' }"
      >
        <!-- ── Resize handle ──────────────────────────────────────────────── -->
        <div
          class="absolute -left-1 top-0 bottom-0 w-2 cursor-col-resize z-10 group/rz"
          @mousedown="startResize"
        >
          <div class="absolute inset-y-0 left-1/2 w-px bg-surface-600 group-hover/rz:bg-brand-500 transition-colors duration-150" />
        </div>

        <!-- ── Panel surface ─────────────────────────────────────────────── -->
        <div
          class="flex flex-col h-full w-full bg-surface-900 border-l border-surface-600 shadow-2xl"
          :class="{ 'border-l-brand-500 ring-1 ring-brand-500/30': isDragging }"
        >

          <!-- ── Sticky header ─────────────────────────────────────────── -->
          <div class="shrink-0 px-4 pt-4 pb-3 border-b border-surface-700">
            <div class="flex items-center justify-between mb-1">
              <h2 class="text-sm font-bold text-slate-100 flex items-center gap-2">
                <UploadCloud :size="16" class="text-brand-400" />
                Uploads
              </h2>
              <button
                @click="emit('close')"
                class="p-1 rounded text-surface-300 hover:text-slate-100 hover:bg-surface-700 transition-colors"
                title="Close panel"
              >
                <X :size="16" />
              </button>
            </div>

            <p class="text-[11px] text-surface-300 mb-2 min-h-[14px]">
              {{ summaryLine || 'No files yet' }}
            </p>

            <!-- Overall progress bar -->
            <div class="h-0.5 bg-surface-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-brand-500 rounded-full"
                :style="{ width: overallPct + '%', transition: 'width 300ms ease-out' }"
              />
            </div>
          </div>

          <!-- ── Scrollable body ───────────────────────────────────────── -->
          <div class="flex-1 overflow-y-auto p-3 relative min-h-0">

            <!-- Drop overlay (when dragging files over the page) -->
            <Transition name="drop-overlay">
              <div
                v-if="isDragging"
                class="absolute inset-2 z-10 flex flex-col items-center justify-center gap-3
                       bg-surface-900/95 border-2 border-dashed border-brand-500 rounded-xl pointer-events-none"
              >
                <UploadCloud :size="36" class="text-brand-400" />
                <p class="text-sm font-semibold text-brand-300">Drop files here</p>
              </div>
            </Transition>

            <!-- Empty state -->
            <div
              v-if="store.queue.length === 0"
              class="flex flex-col items-center justify-center gap-4 py-16 text-center"
            >
              <div class="w-16 h-16 rounded-2xl bg-surface-800 border-2 border-dashed border-surface-600 flex items-center justify-center"
                   :class="{ 'border-brand-500': isDragging }">
                <UploadCloud :size="28" class="text-surface-400" :class="{ 'text-brand-400': isDragging }" />
              </div>
              <div>
                <p class="text-sm font-medium text-slate-200 mb-1">Drop files here</p>
                <p class="text-xs text-surface-300">or click <strong class="text-slate-300">Add files</strong> below</p>
                <p class="text-[10px] text-surface-400 mt-1">Accepts .xlsx, .xls, .csv</p>
              </div>
            </div>

            <!-- File list -->
            <TransitionGroup
              v-else
              name="file-row"
              tag="div"
              class="flex flex-col gap-2"
            >
              <FileRow
                v-for="entry in store.queue"
                :key="entry.id"
                :entry="entry"
                @remove="store.removeEntry"
                @retry="store.retryEntry"
              />
            </TransitionGroup>
          </div>

          <!-- ── Sticky footer ─────────────────────────────────────────── -->
          <div class="shrink-0 px-3 py-3 border-t border-surface-700 flex items-center gap-2 flex-wrap">
            <AppButton size="sm" variant="secondary" @click="triggerFileInput">
              <Plus :size="14" />
              Add files
            </AppButton>
            <AppButton size="sm" variant="secondary" @click="triggerFolderInput">
              <Folder :size="14" />
              Add folder
            </AppButton>

            <div class="flex-1" />

            <button
              v-if="hasActive"
              @click="handleCancelRemaining"
              class="text-xs text-surface-300 hover:text-red-400 transition-colors px-2 py-1"
            >
              Cancel remaining
            </button>

            <AppButton
              v-if="store.errorCount > 0"
              size="sm"
              variant="secondary"
              @click="store.retryFailed"
            >
              <RotateCcw :size="13" />
              Retry failed
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Hidden file input -->
    <input ref="fileInput" type="file" class="hidden" accept=".xlsx,.xls,.csv" multiple @change="onFileInputChange"/>
    <!-- Hidden folder input -->
    <input ref="folderInput" type="file" class="hidden" webkitdirectory multiple @change="onFolderInputChange"/>

    <!-- ── Folder preview modal ─────────────────────────────────────────────── -->
    <Transition name="drop-overlay">
      <div v-if="showFolderModal"
        class="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="showFolderModal = false">
        <div class="bg-surface-900 border border-surface-600 rounded-2xl shadow-2xl flex flex-col w-[480px] max-h-[80vh]">

          <!-- Header -->
          <div class="flex items-center gap-3 px-5 py-4 border-b border-surface-700 flex-shrink-0">
            <div class="w-8 h-8 rounded-xl bg-brand-500/15 flex items-center justify-center flex-shrink-0">
              <Folder :size="15" class="text-brand-400"/>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-bold text-slate-100 truncate">{{ folderName }}</div>
              <div class="text-xs text-surface-400">
                {{ folderFiles.length }} file{{ folderFiles.length !== 1 ? 's' : '' }} found
                · {{ folderSelectedCount }} selected
              </div>
            </div>
            <button @click="showFolderModal = false" class="text-surface-400 hover:text-slate-100 transition-colors p-1">
              <X :size="15"/>
            </button>
          </div>

          <!-- Toolbar -->
          <div class="flex items-center gap-2 px-4 py-2.5 border-b border-surface-700 flex-shrink-0">
            <button @click="selectAllNew"
              class="text-[11px] font-semibold text-brand-400 hover:text-brand-300 transition-colors">
              Select new ({{ folderNewCount }})
            </button>
            <span class="text-surface-600 text-xs">·</span>
            <button @click="toggleAll(true)"  class="text-[11px] text-surface-300 hover:text-slate-100 transition-colors">All</button>
            <span class="text-surface-600 text-xs">·</span>
            <button @click="toggleAll(false)" class="text-[11px] text-surface-300 hover:text-slate-100 transition-colors">None</button>
          </div>

          <!-- File list -->
          <div class="flex-1 overflow-y-auto px-3 py-2 space-y-1 min-h-0">
            <label v-for="(item, i) in folderFiles" :key="i"
              class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-surface-800 transition-colors cursor-pointer group">
              <!-- Checkbox -->
              <component
                :is="item.selected ? CheckSquare : Square"
                :size="15"
                :class="item.selected ? 'text-brand-400' : 'text-surface-500 group-hover:text-surface-300'"
                class="flex-shrink-0 transition-colors"/>
              <input type="checkbox" v-model="item.selected" class="hidden"/>

              <!-- File name + size -->
              <div class="flex-1 min-w-0">
                <div class="text-xs font-mono text-slate-200 truncate">{{ item.file.name }}</div>
                <div class="text-[10px] text-surface-400">{{ (item.file.size / 1024).toFixed(1) }} KB</div>
              </div>

              <!-- Status badge -->
              <div class="flex-shrink-0">
                <span v-if="item.queueStatus === 'new'"
                  class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/30">
                  <CheckCircle2 :size="10"/> New
                </span>
                <span v-else-if="item.queueStatus === 'pending' || item.queueStatus === 'uploading'"
                  class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  <Clock :size="10"/> In Queue
                </span>
                <span v-else-if="item.queueStatus === 'done'"
                  class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-brand-500/15 text-brand-400 border border-brand-500/30">
                  <CheckCircle2 :size="10"/> Uploaded
                </span>
                <span v-else-if="item.queueStatus === 'error'"
                  class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
                  <XCircle :size="10"/> Failed
                </span>
              </div>
            </label>
          </div>

          <!-- Footer -->
          <div class="flex gap-2 px-4 py-3 border-t border-surface-700 flex-shrink-0">
            <button @click="showFolderModal = false"
              class="flex-1 px-3 py-2 rounded-lg text-xs font-semibold text-surface-200 bg-surface-700 hover:bg-surface-600 transition-colors">
              Cancel
            </button>
            <button @click="submitFolderUpload" :disabled="folderSelectedCount === 0"
              class="flex-1 px-3 py-2 rounded-lg text-xs font-semibold text-white bg-brand-500 hover:bg-brand-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
              Upload {{ folderSelectedCount > 0 ? `${folderSelectedCount} file${folderSelectedCount !== 1 ? 's' : ''}` : '' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Duplicate filename confirmation ──────────────────────────────────── -->
    <Transition name="drop-overlay">
      <div v-if="showDupeModal"
        class="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="showDupeModal = false">
        <div class="bg-surface-900 border border-surface-600 rounded-2xl p-5 w-96 shadow-2xl">
          <div class="flex items-center gap-2.5 mb-3">
            <div class="w-8 h-8 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
              <RotateCcw :size="15" class="text-amber-400"/>
            </div>
            <div>
              <div class="text-sm font-bold text-slate-100">Duplicate filenames</div>
              <div class="text-xs text-surface-400">
                {{ dupeNames.length }} file{{ dupeNames.length > 1 ? 's' : '' }} already in queue
              </div>
            </div>
          </div>

          <!-- List of dupe names -->
          <div class="bg-surface-800 rounded-xl px-3 py-2 mb-4 max-h-40 overflow-y-auto space-y-1">
            <div v-for="name in dupeNames" :key="name"
              class="text-xs text-amber-300 font-mono truncate flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0"/>
              {{ name }}
            </div>
          </div>

          <div class="flex gap-2">
            <button @click="confirmSkipAll"
              class="flex-1 px-3 py-2 rounded-lg text-xs font-semibold text-surface-200 bg-surface-700 hover:bg-surface-600 transition-colors">
              Skip duplicates
            </button>
            <button @click="confirmUploadAll"
              class="flex-1 px-3 py-2 rounded-lg text-xs font-semibold text-white bg-brand-500 hover:bg-brand-400 transition-colors">
              Upload all
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style>
/* ── Panel slide-in from right ──────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .upload-panel-enter-active,
  .upload-panel-leave-active {
    transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1);
  }
}
.upload-panel-enter-from,
.upload-panel-leave-to {
  transform: translateX(100%);
}

/* ── File row enter animation ───────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .file-row-enter-active {
    transition: opacity 150ms ease-out, transform 150ms ease-out;
  }
}
.file-row-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

/* ── Drop overlay fade ──────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .drop-overlay-enter-active,
  .drop-overlay-leave-active {
    transition: opacity 120ms ease;
  }
}
.drop-overlay-enter-from,
.drop-overlay-leave-to {
  opacity: 0;
}

/* ── Indeterminate progress bar ─────────────────────────────────────────────── */
@media (prefers-reduced-motion: no-preference) {
  .upload-indeterminate-bar {
    width: 35% !important;
    animation: upload-indeterminate 1.2s ease-in-out infinite;
  }

  @keyframes upload-indeterminate {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }
}
@media (prefers-reduced-motion: reduce) {
  .upload-indeterminate-bar {
    width: 60% !important;
  }
}
</style>
