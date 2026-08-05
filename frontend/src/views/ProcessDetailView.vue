<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import { useLinesStore } from '@/stores/lines'
import { useAuthStore } from '@/stores/auth'
import { useStationsStore } from '@/stores/stations'
import { useToast } from '@/composables/useToast'
import AppCard   from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppBadge  from '@/components/ui/AppBadge.vue'
import AppInput  from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'
import { ChevronRight, Download, Upload, FileSpreadsheet, CheckCircle2, Maximize2, Minimize2, Loader2, RotateCcw } from 'lucide-vue-next'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import type { ProcessVersion } from '@/stores/stations'
import { versionsService } from '@/services/versions.service'
import { blobWithProgress } from '@/services/api'
import AIStatusBadge from '@/components/ui/AIStatusBadge.vue'
import { useAIStatusStore } from '@/stores/aiStatus'

const route  = useRoute()
const router = useRouter()
const auth    = useAuthStore()
const stStore = useStationsStore()
const { toast } = useToast()
const aiStatusStore = useAIStatusStore()
const aiStatus = computed(() => aiStatusStore.getStatus(processId.value))

const lineId       = computed(() => route.params.lineId as string)
const processId    = computed(() => route.params.processId as string)
const carModelName = computed(() =>
  (route.query.car as string | undefined) || process.value?.carModel?.name || '',
)

const process = computed(() => {
  const stns = stStore.stations[lineId.value] ?? []
  for (const stn of stns) {
    const p = stn.processes.find(p => p.id === processId.value)
    if (p) return p
  }
  return null
})

const tab    = ref('overview')
const tabs   = computed(() => ['overview', 'versions', ...(auth.isPM ? ['upload'] : [])])
const linesStore = useLinesStore()
const line       = computed(() => linesStore.lines.find(l => l.id === lineId.value))

const versions = ref<ProcessVersion[]>([])
const loading  = ref(false)

onMounted(async () => {
  if (!processId.value) return
  if (!(stStore.stations[lineId.value]?.length)) {
    await stStore.fetchStations(lineId.value)
  }
  // Seed AI status from loaded process then connect SSE
  if (process.value) aiStatusStore.seedFromProcesses([process.value])
  aiStatusStore.connect()

  loading.value = true
  try {
    versions.value = await stStore.fetchProcessVersions(processId.value)
    if (versions.value[0]) selectedVersionId.value = versions.value[0].id
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.back()
}

const latestVersion = computed(() => versions.value[0] ?? null)

// ─── Upload ───────────────────────────────────────────────────────────────────
const commitMsg  = ref('')
const pickedFile = ref<File | null>(null)
const uploading  = ref(false)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  pickedFile.value = input.files?.[0] ?? null
}

async function handleUpload() {
  if (!commitMsg.value.trim()) { toast('Commit message required', 'error'); return }
  if (!pickedFile.value)       { toast('Please select a file', 'error');    return }
  uploading.value = true
  try {
    await stStore.uploadVersion(
      process.value!.lineId,
      process.value!.stationId,
      process.value!.id,
      commitMsg.value,
      pickedFile.value,
    )
    versions.value = await stStore.fetchProcessVersions(processId.value)
    toast(`Control Plan v${versions.value.length}.0 uploaded!`)
    commitMsg.value = ''; pickedFile.value = null; tab.value = 'versions'
    // refresh right panel to show the newly uploaded version
    loadedForVersion.value = null
    if (versions.value[0]) selectedVersionId.value = versions.value[0].id
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { uploading.value = false }
}

const statusColor: Record<string, string> = { active: '#10B981', archived: '#475569' }

// ─── PDF viewer ───────────────────────────────────────────────────────────────
const selectedVersionId = ref<string | null>(null)
const selectedVersion   = computed(() => versions.value.find(v => v.id === selectedVersionId.value) ?? null)

const pdfUrl           = ref<string | null>(null)
const pdfLoading       = ref(false)
const pdfError         = ref<string | null>(null)
const loadedForVersion = ref<string | null>(null)

async function loadPdf(version: ProcessVersion) {
  if (loadedForVersion.value === version.id) return
  pdfLoading.value = true
  pdfError.value   = null
  if (pdfUrl.value) { URL.revokeObjectURL(pdfUrl.value); pdfUrl.value = null }
  try {
    const blob = await versionsService.getPdf(processId.value, version.id)
    pdfUrl.value           = URL.createObjectURL(blob)
    loadedForVersion.value = version.id
  } catch (e: unknown) {
    pdfError.value = (e as Error).message ?? 'Failed to load PDF'
  } finally {
    pdfLoading.value = false
  }
}

watch(selectedVersion, v => { if (v) loadPdf(v) })
onUnmounted(() => { if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value) })

// ─── Fullscreen ────────────────────────────────────────────────────────────────
const rightPanelEl  = ref<HTMLElement | null>(null)
const isFullscreen  = ref(false)

function onFsChange() { isFullscreen.value = !!document.fullscreenElement }
onMounted(()    => document.addEventListener('fullscreenchange', onFsChange))
onUnmounted(()  => document.removeEventListener('fullscreenchange', onFsChange))

function toggleFullscreen() {
  if (!rightPanelEl.value) return
  document.fullscreenElement ? document.exitFullscreen() : rightPanelEl.value.requestFullscreen()
}

// ── Download progress tracking ────────────────────────────────────────────────
// key: `${versionId}:xlsx` | `${versionId}:highlighted`
// value: 0 = preparing, 1–99 = progress %, -1 = indeterminate
const downloads = ref<Record<string, number>>({})

function dlState(versionId: string, type: 'xlsx' | 'highlighted'): number | null {
  const key = `${versionId}:${type}`
  return key in downloads.value ? downloads.value[key] : null
}
function dlLabel(pct: number | null): string {
  if (pct === null)  return 'Download'
  if (pct === -1)    return 'Downloading…'
  if (pct === 0)     return 'Preparing…'
  return `${pct}%`
}
function hlLabel(pct: number | null): string {
  if (pct === null)  return 'Highlighted'
  if (pct === -1)    return 'Downloading…'
  if (pct === 0)     return 'Preparing…'
  return `${pct}%`
}

function setDl(versionId: string, type: 'xlsx' | 'highlighted', val: number) {
  downloads.value = { ...downloads.value, [`${versionId}:${type}`]: val }
}
function clearDl(versionId: string, type: 'xlsx' | 'highlighted') {
  const next = { ...downloads.value }
  delete next[`${versionId}:${type}`]
  downloads.value = next
}

async function downloadFile(version: ProcessVersion) {
  if (dlState(version.id, 'xlsx') !== null) return
  setDl(version.id, 'xlsx', 0)
  try {
    const blob = await blobWithProgress(
      `/processes/${processId.value}/versions/${version.id}/download`,
      pct => setDl(version.id, 'xlsx', pct),
    )
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `${process.value?.code ?? 'control-plan'}_${version.version}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast('Download failed', 'error')
  } finally {
    clearDl(version.id, 'xlsx')
  }
}

async function downloadHighlighted(version: ProcessVersion) {
  if (dlState(version.id, 'highlighted') !== null) return
  setDl(version.id, 'highlighted', 0)
  try {
    const blob = await blobWithProgress(
      `/processes/${processId.value}/versions/${version.id}/highlighted`,
      pct => setDl(version.id, 'highlighted', pct),
    )
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `highlighted_${version.version}_${process.value?.code ?? 'control-plan'}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast('Highlighted download failed', 'error')
  } finally {
    clearDl(version.id, 'highlighted')
  }
}

// Remap version labels from array position so they stay consistent after restores
function vLabel(v: ProcessVersion): string {
  const idx = versions.value.indexOf(v)
  return idx === -1 ? v.version : `v${versions.value.length - idx}.0`
}
function nextVersionLabel(): string {
  return `v${versions.value.length + 1}.0`
}

const expandedVersions = ref<Set<string>>(new Set())
function toggleExpanded(id: string) {
  expandedVersions.value.has(id)
    ? expandedVersions.value.delete(id)
    : expandedVersions.value.add(id)
  expandedVersions.value = new Set(expandedVersions.value) // trigger reactivity
}

// ─── Restore version ──────────────────────────────────────────────────────────
const restoreTarget   = ref<ProcessVersion | null>(null)
const restoring       = ref(false)

function promptRestore(v: ProcessVersion) {
  restoreTarget.value = v
}

async function confirmRestore() {
  if (!restoreTarget.value) return
  const { id: versionId, version: versionLabel } = restoreTarget.value
  restoring.value = true
  try {
    await versionsService.restore(processId.value, versionId)
    versions.value = await stStore.fetchProcessVersions(processId.value)
    loadedForVersion.value = null
    if (versions.value[0]) selectedVersionId.value = versions.value[0].id
    toast(`Restored to ${versionLabel}`)
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    restoring.value = false
    restoreTarget.value = null
  }
}

</script>

<template>
  <div class="overflow-hidden" style="height:100svh">
  <SplitterGroup direction="horizontal" class="h-full">

    <!-- ── LEFT PANEL: process details ── -->
    <SplitterPanel :default-size="55" :min-size="35" class="overflow-hidden h-full">
      <div class="h-full flex flex-col overflow-hidden px-8 pt-8">

        <!-- Breadcrumb -->
        <div class="flex items-center gap-1.5 text-xs text-surface-200 mb-5 flex-shrink-0">
          <button @click="goBack()" class="text-brand-400 hover:text-brand-300 font-bold transition-colors">
            {{ line?.name }}
          </button>
          <ChevronRight :size="12"/>
          <span>{{ process?.stationName }}</span>
          <ChevronRight :size="12"/>
          <span class="text-slate-300 font-semibold">{{ process?.name }}</span>
        </div>

        <!-- Header -->
        <AppCard class="mb-5 flex-shrink-0" :style="{ borderLeft: `3px solid ${line?.color}` }">
          <div class="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div class="flex items-center gap-2 mb-2 flex-wrap">
                <code class="text-xs text-surface-200 bg-surface-950 border border-surface-600 px-2 py-0.5 rounded-md font-mono">{{ process?.code }}</code>
                <AppBadge :color="line?.color">{{ line?.name }}</AppBadge>
                <AppBadge :color="statusColor[process?.status] || '#475569'">{{ process?.status }}</AppBadge>
                <AppBadge v-if="process?.hasMissingCP" color="#EF4444">Missing CP</AppBadge>
              </div>
              <div class="flex items-center gap-3">
                <h1 class="text-2xl font-black text-slate-100">{{ process?.name }}</h1>
                <AIStatusBadge :status="aiStatus"/>
              </div>
              <p class="text-sm text-surface-200 mt-1">{{ process?.stationName }} · {{ carModelName }}</p>
            </div>
            <div class="flex gap-2">
              <AppButton v-if="auth.isPM" @click="tab = 'upload'" :style="{ background: line?.color }">
                <Upload :size="15"/> Upload New Version
              </AppButton>
              <AppButton variant="secondary" @click="goBack()">← Back</AppButton>
            </div>
          </div>
        </AppCard>

        <!-- Quick stats -->
        <div class="grid grid-cols-5 gap-3 mb-5 flex-shrink-0">
          <AppCard v-for="s in [
            { label:'Total Versions',   value: versions.length || 0,                                                          color: line?.color },
            { label:'Latest Version',   value: latestVersion ? vLabel(latestVersion) : 'None',                             color:'#E2E8F0' },
            { label:'Last Updated',     value: latestVersion ? new Date(latestVersion.uploadedAt).toLocaleDateString() : '—', color:'#E2E8F0' },
            { label:'Cell Changes',     value: versions.reduce((a,v)=>a+v.changes,0),                                        color:'#10B981' },
            { label:'Shape Additions',  value: versions.reduce((a,v)=>a+v.shapeAdded,0),                                     color:'#F59E0B' },
          ]" :key="s.label" class="p-4">
            <div class="text-xl font-black font-mono" :style="{ color: s.color }">{{ s.value }}</div>
            <div class="text-xs text-surface-200 mt-1">{{ s.label }}</div>
          </AppCard>
        </div>

        <!-- Tabs -->
        <div class="flex gap-0 border-b border-surface-700 mb-5 flex-shrink-0">
          <button v-for="t in tabs" :key="t" @click="tab = t"
            :class="['px-4 py-2.5 text-sm font-semibold capitalize transition-colors border-b-2 -mb-px',
                    tab === t ? 'border-current' : 'border-transparent text-surface-200 hover:text-slate-300']"
            :style="tab === t ? { color: line?.color, borderColor: line?.color } : {}">
            {{ t }}
          </button>
        </div>

        <!-- Tab content — scrolls independently -->
        <div class="flex-1 overflow-y-auto min-h-0 pb-8">

          <!-- OVERVIEW -->
          <div v-if="tab === 'overview'" class="grid grid-cols-2 gap-5">
            <AppCard>
              <h3 class="text-sm font-bold text-slate-100 mb-4">Process Info</h3>
              <div v-for="[k,v,mono] in [
                ['Process Code', process?.code,           true],
                ['Station',      process?.stationName,    false],
                ['Line',         line?.name,              false],
                ['Car Model',    carModelName,            false],
                ['Status',       process?.status,         false],
              ]" :key="k" class="flex justify-between py-2.5 border-b border-surface-700 last:border-0">
                <span class="text-xs text-surface-200">{{ k }}</span>
                <span :class="['text-xs font-semibold text-slate-300', mono && 'font-mono']">{{ v }}</span>
              </div>
            </AppCard>
            <AppCard>
              <h3 class="text-sm font-bold text-slate-100 mb-4">Latest Version</h3>
              <template v-if="latestVersion">
                <div v-for="[k,v] in [
                  ['Version',    vLabel(latestVersion)],
                  ['Uploaded by',latestVersion.uploadedBy],
                  ['Date',       new Date(latestVersion.uploadedAt).toLocaleDateString()],
                  ['File size',  latestVersion.fileSize],
                  ['Changes',    `+${latestVersion.changes} modifications`],
                ]" :key="k" class="flex justify-between py-2.5 border-b border-surface-700 last:border-0">
                  <span class="text-xs text-surface-200">{{ k }}</span>
                  <span class="text-xs font-semibold text-slate-300">{{ v }}</span>
                </div>
                <div class="mt-3 p-3 bg-surface-950 border border-surface-600 rounded-lg">
                  <span class="text-xs text-surface-300">Commit: </span>
                  <span class="text-xs text-slate-300 italic">"{{ latestVersion.commitMessage }}"</span>
                </div>
              </template>
              <div v-else class="text-center py-8 text-surface-300 text-sm">No control plan uploaded yet</div>
            </AppCard>
          </div>

          <!-- VERSIONS -->
          <div v-if="tab === 'versions'">
            <h3 class="text-sm font-bold text-slate-100 mb-4">
              Version History — {{ versions.length }} version{{ versions.length !== 1 ? 's' : '' }}
            </h3>
            <div v-if="loading" class="text-center py-10 text-surface-300">Loading versions…</div>
            <div v-else-if="!versions.length" class="text-center py-10 text-surface-300">No versions uploaded yet.</div>
            <div v-for="(v, idx) in (auth.isLM ? versions.slice(0, 1) : versions)" :key="v.id" class="mb-3">
              <AppCard :style="idx === 0 ? { borderLeft: `2px solid ${line?.color}` } : {}">
                <div class="flex items-start gap-4">

                  <!-- Version badge -->
                  <div class="w-12 h-12 rounded-xl flex items-center justify-center font-mono text-xs font-bold flex-shrink-0 border"
                      :style="idx === 0
                        ? { background: line?.color+'22', color: line?.color, borderColor: line?.color+'44' }
                        : { background:'#0F1623', color:'#475569', borderColor:'#1E2D45' }">
                    {{ vLabel(v) }}
                  </div>

                  <!-- Middle: commit + meta + diff pills -->
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="text-sm font-bold text-slate-200">{{ v.commitMessage }}</span>
                      <AppBadge v-if="idx === 0" :color="line?.color">LATEST</AppBadge>
                    </div>
                    <p class="text-xs text-surface-200 mb-2">
                      {{ v.uploadedBy }} · {{ new Date(v.uploadedAt).toLocaleDateString() }} · {{ v.fileSize }}
                    </p>

                    <!-- Diff pills -->
                    <div v-if="v.diffRows.length" class="mb-2">
                      <div class="flex items-center gap-2 flex-wrap">
                        <div v-for="(r, i) in v.diffRows.slice(0, 4)" :key="i"
                            :class="['border rounded px-2 py-1 text-xs', r.type === 'shape'
                              ? 'bg-amber-500/5 border-amber-500/30'
                              : 'bg-surface-950 border-surface-600']">
                          <span :class="r.type === 'shape' ? 'text-amber-400/70' : 'text-surface-200'">{{ r.field }}: </span>
                          <span v-if="r.old" class="text-red-400 line-through">{{ r.old }}</span>
                          <span v-if="r.old && r.newVal" class="text-surface-300"> → </span>
                          <span v-if="r.newVal" class="text-emerald-400">{{ r.newVal }}</span>
                        </div>

                        <button v-if="v.diffRows.length > 4" @click="toggleExpanded(v.id)"
                          class="text-xs text-surface-300 hover:text-slate-200 transition-colors px-1.5 py-1 rounded border border-surface-700 hover:border-surface-500">
                          {{ expandedVersions.has(v.id) ? '− less' : `+${v.diffRows.length - 4} more` }}
                        </button>
                      </div>

                      <div v-if="expandedVersions.has(v.id)" class="flex gap-2 flex-wrap mt-2 pt-2 border-t border-surface-800">
                        <div v-for="(r, i) in v.diffRows.slice(4)" :key="i"
                            :class="['border rounded px-2 py-1 text-xs', r.type === 'shape'
                              ? 'bg-amber-500/5 border-amber-500/30'
                              : 'bg-surface-950 border-surface-600']">
                          <span :class="r.type === 'shape' ? 'text-amber-400/70' : 'text-surface-200'">{{ r.field }}: </span>
                          <span v-if="r.old" class="text-red-400 line-through">{{ r.old }}</span>
                          <span v-if="r.old && r.newVal" class="text-surface-300"> → </span>
                          <span v-if="r.newVal" class="text-emerald-400">{{ r.newVal }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Extracted metadata -->
                    <div class="flex items-center gap-2">
                      <div class="flex items-center gap-1.5 bg-surface-900 border border-surface-700 rounded-md px-2 py-1">
                        <span class="text-[9px] text-surface-100 uppercase tracking-wider">name</span>
                        <span class="text-[11px] font-bold text-slate-200 font-mono">{{ v.extractedData.name }}</span>
                      </div>
                      <div class="flex items-center gap-1.5 bg-surface-900 border border-surface-700 rounded-md px-2 py-1">
                        <span class="text-[9px] text-surface-100 uppercase tracking-wider">doc</span>
                        <span class="text-[11px] font-bold text-slate-200 font-mono">{{ v.extractedData.date }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Right: stats + download -->
                  <div class="flex-shrink-0 flex flex-col items-end gap-2">
                    <div class="flex gap-3">
                      <div class="text-right">
                        <div class="text-lg font-black text-emerald-400 font-mono leading-tight">{{ v.changes }}</div>
                        <div class="text-[10px] text-surface-300">cell changes</div>
                      </div>
                      <div class="text-right">
                        <div class="text-lg font-black text-amber-400 font-mono leading-tight">{{ v.shapeAdded }}</div>
                        <div class="text-[10px] text-surface-300">shapes added</div>
                      </div>
                      <div v-if="v.shapeRemoved" class="text-right">
                        <div class="text-lg font-black text-red-400 font-mono leading-tight">{{ v.shapeRemoved }}</div>
                        <div class="text-[10px] text-surface-300">shapes removed</div>
                      </div>
                    </div>
                    <button v-if="!auth.isLM || versions.length === 1" @click="downloadFile(v)"
                      :disabled="dlState(v.id, 'xlsx') !== null"
                      class="text-xs text-brand-400 hover:text-brand-300 border border-surface-600 rounded px-2 py-1 flex items-center gap-1 transition-colors disabled:opacity-60 disabled:cursor-not-allowed min-w-[80px] justify-center">
                      <Loader2 v-if="dlState(v.id, 'xlsx') !== null" :size="11" class="animate-spin shrink-0"/>
                      <Download v-else :size="11" class="shrink-0"/>
                      {{ dlLabel(dlState(v.id, 'xlsx')) }}
                    </button>
                    <button v-if="versions.length > 1 && (idx < versions.length - 1 || auth.isLM)" @click="downloadHighlighted(v)"
                      :disabled="dlState(v.id, 'highlighted') !== null"
                      class="text-xs text-emerald-400 hover:text-emerald-300 border border-surface-600 rounded px-2 py-1 flex items-center gap-1 transition-colors disabled:opacity-60 disabled:cursor-not-allowed min-w-[90px] justify-center">
                      <Loader2 v-if="dlState(v.id, 'highlighted') !== null" :size="11" class="animate-spin shrink-0"/>
                      <Download v-else :size="11" class="shrink-0"/>
                      {{ hlLabel(dlState(v.id, 'highlighted')) }}
                    </button>
                    <button v-if="auth.isPM && idx > 0" @click="promptRestore(v)"
                      class="text-xs text-amber-400 hover:text-amber-300 border border-surface-600 rounded px-2 py-1 flex items-center gap-1 transition-colors">
                      <RotateCcw :size="11"/> Restore
                    </button>
                  </div>

                </div>
              </AppCard>
            </div>
          </div>

          <!-- UPLOAD -->
          <div v-if="tab === 'upload'" class="max-w-lg">
            <h3 class="text-sm font-bold text-slate-100 mb-5">Upload New Control Plan Version</h3>
            <div v-if="latestVersion" class="flex justify-between mb-4 p-3 bg-surface-900 border border-surface-600 rounded-lg">
              <span class="text-xs text-surface-200">Current: <strong class="font-mono" :style="{ color: line?.color }">{{ vLabel(latestVersion) }}</strong></span>
              <span class="text-xs text-surface-200">Next: <strong class="text-emerald-400 font-mono">{{ nextVersionLabel() }}</strong></span>
            </div>
            <label :class="['block border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all mb-5',
                            pickedFile ? 'border-brand-500 bg-brand-500/5' : 'border-surface-600 hover:border-surface-500']">
              <input type="file" accept=".xlsx,.csv,.xls" class="sr-only" @change="onFileChange"/>
              <div class="flex justify-center mb-2">
                <CheckCircle2 v-if="pickedFile" :size="40" :style="{ color: line?.color }" />
                <FileSpreadsheet v-else :size="40" class="text-surface-400" />
              </div>
              <div v-if="pickedFile" class="text-sm font-semibold" :style="{ color: line?.color }">{{ pickedFile.name }}</div>
              <template v-else>
                <div class="text-sm font-semibold text-slate-300 mb-1">Click to select file (.xlsx / .csv)</div>
                <div class="text-xs text-surface-200">Max 50 MB</div>
              </template>
            </label>
            <FormField label="Commit Message" :required="true" class="mb-5">
              <AppInput v-model="commitMsg" placeholder="Describe what changed in this version…"/>
            </FormField>
            <AppButton class="w-full justify-center py-3" :style="{ background: line?.color }" :loading="uploading" :disabled="uploading" @click="handleUpload">
              <Upload v-if="!uploading" :size="16"/> {{ uploading ? 'Uploading…' : 'Upload Control Plan' }}
            </AppButton>
          </div>

        </div><!-- /tab content -->
      </div><!-- /left panel inner -->
    </SplitterPanel>

    <!-- ── RESIZE HANDLE ── -->
    <SplitterResizeHandle class="group relative flex w-1.5 items-center justify-center bg-surface-800 cursor-col-resize transition-colors hover:bg-surface-700 data-[state=drag]:bg-brand-500/30">
      <div class="h-10 w-0.5 rounded-full bg-surface-600 transition-colors group-hover:bg-brand-400 group-data-[state=drag]:bg-brand-400"/>
    </SplitterResizeHandle>

    <!-- ── RIGHT PANEL: Spreadsheet viewer ── -->
    <SplitterPanel :default-size="45" :min-size="25" class="overflow-hidden h-full">
      <div ref="rightPanelEl" class="h-full flex flex-col bg-white">

        <div class="flex items-center gap-2 px-3 py-2 bg-surface-900 border-b border-surface-700 flex-shrink-0">
          <select v-if="versions.length && !auth.isLM" v-model="selectedVersionId"
            class="bg-surface-800 border border-surface-600 text-slate-200 text-xs font-mono rounded px-2 py-1 cursor-pointer focus:outline-none focus:border-brand-500 transition-colors">
            <option v-for="v in versions" :key="v.id" :value="v.id">
              {{ vLabel(v) }} — {{ v.commitMessage }}
            </option>
          </select>
          <span v-else-if="!versions.length" class="text-xs text-surface-400">No versions yet</span>
          <span v-else-if="auth.isLM && selectedVersion" class="text-xs text-slate-300 font-mono">{{ vLabel(selectedVersion) }} — {{ selectedVersion.commitMessage }}</span>

          <div class="flex items-center gap-1.5 ml-auto flex-shrink-0">
            <template v-if="selectedVersion && versions.length > 1 && selectedVersionId !== versions[versions.length - 1]?.id">
              <span v-for="l in [
                { label:'Modified',    bg:'#DCFCE7', text:'#14532D' },
              ]" :key="l.label"
                class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                :style="{ background: l.bg, color: l.text }">
                {{ l.label }}
              </span>
            </template>
            <button v-if="selectedVersion && (!auth.isLM || versions.length === 1)" @click="downloadFile(selectedVersion)"
              :disabled="dlState(selectedVersion.id, 'xlsx') !== null"
              class="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 border border-surface-600 rounded px-2 py-1 transition-colors disabled:opacity-60 disabled:cursor-not-allowed min-w-[80px] justify-center">
              <Loader2 v-if="dlState(selectedVersion.id, 'xlsx') !== null" :size="11" class="animate-spin shrink-0"/>
              <Download v-else :size="11" class="shrink-0"/>
              {{ dlLabel(dlState(selectedVersion.id, 'xlsx')) }}
            </button>
            <button v-if="selectedVersion && versions.length > 1 && selectedVersionId !== versions[versions.length - 1]?.id" @click="downloadHighlighted(selectedVersion)"
              :disabled="dlState(selectedVersion.id, 'highlighted') !== null"
              class="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 border border-surface-600 rounded px-2 py-1 transition-colors disabled:opacity-60 disabled:cursor-not-allowed min-w-[90px] justify-center">
              <Loader2 v-if="dlState(selectedVersion.id, 'highlighted') !== null" :size="11" class="animate-spin shrink-0"/>
              <Download v-else :size="11" class="shrink-0"/>
              {{ hlLabel(dlState(selectedVersion.id, 'highlighted')) }}
            </button>
            <button @click="toggleFullscreen"
              class="flex items-center justify-center w-6 h-6 text-surface-300 hover:text-slate-200 border border-surface-600 rounded transition-colors">
              <Minimize2 v-if="isFullscreen" :size="12"/>
              <Maximize2 v-else :size="12"/>
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-hidden relative">
          <!-- Loading -->
          <div v-if="pdfLoading" class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-950 text-surface-400">
            <Loader2 :size="32" class="animate-spin opacity-60"/>
            <span class="text-sm">Generating PDF…</span>
          </div>
          <!-- Error -->
          <div v-else-if="pdfError" class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center px-8 bg-surface-950 text-surface-400">
            <FileSpreadsheet :size="40" class="opacity-30"/>
            <span class="text-sm text-red-400">{{ pdfError }}</span>
            <button v-if="selectedVersion" @click="loadPdf(selectedVersion)"
              class="text-xs text-brand-400 border border-surface-600 rounded px-3 py-1.5 hover:text-brand-300 transition-colors">
              Retry
            </button>
          </div>
          <!-- PDF iframe -->
          <iframe v-else-if="pdfUrl" :src="pdfUrl" class="w-full h-full border-0"/>
          <!-- Empty -->
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-950 text-surface-400">
            <FileSpreadsheet :size="40" class="opacity-30"/>
            <span class="text-sm">No version selected</span>
          </div>
        </div>

      </div>
    </SplitterPanel>

  </SplitterGroup>
  </div>

  <ConfirmDialog
    :open="!!restoreTarget"
    title="Restore Version"
    :message="restoreTarget
      ? `Restoring ${vLabel(restoreTarget)} will permanently delete ${versions.indexOf(restoreTarget)} newer version${versions.indexOf(restoreTarget) !== 1 ? 's' : ''} uploaded after it. This cannot be undone.`
      : ''"
    label="Restore"
    :danger="true"
    @close="restoreTarget = null"
    @confirm="confirmRestore"
  />
</template>