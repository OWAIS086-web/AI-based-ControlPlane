<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FileSpreadsheet, FileIcon, RotateCcw, X } from 'lucide-vue-next'
import type { FileEntry } from '@/stores/uploads'

const props = defineProps<{ entry: FileEntry }>()
const emit  = defineEmits<{ remove: [id: string]; retry: [id: string] }>()

function formatSize(bytes: number): string {
  if (bytes < 1024)           return `${bytes} B`
  if (bytes < 1024 * 1024)   return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const ext           = computed(() => props.entry.file.name.split('.').pop()?.toLowerCase() ?? '')
const isSpreadsheet = computed(() => ['xlsx', 'xls', 'csv'].includes(ext.value))

const badgeClass = computed<string>(() => {
  switch (props.entry.status) {
    case 'created':
    case 'matched':   return 'bg-teal-500/15 text-teal-400 border-teal-800'
    case 'rejected':
    case 'error':     return 'bg-red-500/15 text-red-400 border-red-800'
    case 'uploading': return 'bg-blue-500/15 text-blue-400 border-blue-800'
    default:          return 'bg-surface-700 text-surface-400 border-surface-600'
  }
})

const badgeLabel = computed<string>(() => ({
  pending:   'Pending',
  uploading: 'Uploading',
  created:   'Created',
  matched:   'Matched',
  rejected:  'Rejected',
  error:     'Error',
  cancelled: 'Cancelled',
} as Record<string, string>)[props.entry.status] ?? props.entry.status)

const isIndeterminate = computed(() =>
  props.entry.status === 'uploading' && props.entry.progress === -1,
)

const barFill = computed(() => {
  const { status, progress } = props.entry
  if (status === 'created' || status === 'matched') return { w: '100%', cls: 'bg-teal-500' }
  if (status === 'rejected' || status === 'error')  return { w: '100%', cls: 'bg-red-500' }
  if (status === 'uploading' && progress >= 0)      return { w: `${progress}%`, cls: 'bg-blue-500' }
  return { w: '0%', cls: 'bg-surface-600' }
})

const barLabel = computed<string>(() => {
  const { status, progress, response, error } = props.entry
  if (status === 'pending')   return 'Waiting'
  if (status === 'uploading') return progress === -1 ? 'Uploading…' : `${progress}%`
  if (status === 'created')   return 'Created'
  if (status === 'matched')   return 'Matched'
  if (status === 'rejected')  return response?.message ?? 'Rejected'
  if (status === 'error')     return error ?? 'Upload failed'
  if (status === 'cancelled') return 'Removed'
  return ''
})

const viewRoute = computed(() => {
  const pid = props.entry.response?.process?.id
  return pid
    ? { name: 'process-detail', params: { lineId: props.entry.lineId, processId: pid } }
    : null
})
</script>

<template>
  <div
    class="group relative flex flex-col gap-1.5 px-3 py-2.5 rounded-lg bg-surface-900 border border-surface-700 hover:border-surface-600 transition-colors duration-150"
    :class="{ 'opacity-55': entry.status === 'cancelled' }"
  >
    <!-- Top row: icon · name+size · badge · actions -->
    <div class="flex items-center gap-2 min-w-0">
      <component
        :is="isSpreadsheet ? FileSpreadsheet : FileIcon"
        :size="15"
        :class="['shrink-0', isSpreadsheet ? 'text-emerald-400' : 'text-surface-400']"
      />
      <div class="flex-1 min-w-0">
        <div class="text-xs font-medium text-slate-200 truncate" :title="entry.file.name">
          {{ entry.file.name }}
        </div>
        <div class="text-[10px] text-surface-400">{{ formatSize(entry.file.size) }}</div>
      </div>

      <!-- Status badge -->
      <span
        :class="['shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border transition-colors duration-200', badgeClass]"
      >
        {{ badgeLabel }}
      </span>

      <!-- Contextual actions -->
      <div class="flex items-center gap-1 shrink-0">
        <RouterLink
          v-if="viewRoute"
          :to="viewRoute"
          class="text-[10px] text-brand-400 hover:text-brand-300 font-semibold transition-colors whitespace-nowrap"
        >
          View →
        </RouterLink>
        <button
          v-if="entry.status === 'error'"
          @click="emit('retry', entry.id)"
          class="text-[10px] text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-0.5 transition-colors"
        >
          <RotateCcw :size="10" />
          Retry
        </button>
        <button
          v-if="['pending', 'uploading', 'cancelled', 'error'].includes(entry.status)"
          @click="emit('remove', entry.id)"
          class="opacity-0 group-hover:opacity-100 p-0.5 rounded text-surface-400 hover:text-red-400 transition-all"
          :title="entry.status === 'uploading' ? 'Cancel upload' : 'Remove'"
        >
          <X :size="12" />
        </button>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="h-1 bg-surface-700 rounded-full overflow-hidden">
      <div
        v-if="!isIndeterminate"
        :class="['h-full rounded-full', barFill.cls]"
        :style="{ width: barFill.w, transition: 'width 150ms ease-out' }"
      />
      <div
        v-else
        class="h-full upload-indeterminate-bar rounded-full bg-blue-500"
      />
    </div>

    <!-- Progress label -->
    <div class="text-[10px] text-surface-400 truncate leading-none">{{ barLabel }}</div>

    <!-- Result metadata: extracted code + version (created / matched only) -->
    <div
      v-if="(entry.status === 'created' || entry.status === 'matched') && (entry.response?.extractedCode || entry.response?.version?.version)"
      class="flex items-center gap-1.5 flex-wrap"
    >
      <span
        v-if="entry.response?.version?.version"
        class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border bg-teal-500/10 text-teal-400 border-teal-800 shrink-0"
      >
        {{ entry.response.version.version }}
      </span>
      <span
        v-if="entry.response?.extractedCode"
        class="text-[10px] font-mono text-surface-300 truncate"
        :title="entry.response.extractedCode"
      >
        {{ entry.response.extractedCode }}
      </span>
    </div>
  </div>
</template>
