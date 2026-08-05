<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Component } from 'vue'
import { useLinesStore } from '@/stores/lines'
import type { LineType, Line } from '@/stores/lines'
import { useToast } from '@/composables/useToast'
import AppCard     from '@/components/ui/AppCard.vue'
import AppButton   from '@/components/ui/AppButton.vue'
import AppModal    from '@/components/ui/AppModal.vue'
import AppInput    from '@/components/ui/AppInput.vue'
import FormField   from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PageHeader  from '@/components/ui/PageHeader.vue'
import {
  Plus, Pencil, Trash2, GripVertical,
  Scissors, Wrench, Settings, Building2, Flag,
  Car, Zap, Box, Layers, Package, Cpu, Activity,
  Gauge, Cog, Factory, Hammer, LayoutGrid, Construction,
} from 'lucide-vue-next'

const linesStore = useLinesStore()
const { toast }  = useToast()

// ─── Icon helpers ─────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, Component> = {
  scissors: Scissors, wrench: Wrench, settings: Settings, building2: Building2,
  flag: Flag, car: Car, zap: Zap, box: Box, layers: Layers, package: Package,
  cpu: Cpu, activity: Activity, gauge: Gauge, cog: Cog, factory: Factory,
  hammer: Hammer, grid: LayoutGrid, construction: Construction,
}

const AVAILABLE_ICONS = [
  'scissors', 'wrench', 'settings', 'building2', 'flag',
  'car', 'zap', 'box', 'layers', 'package', 'cpu',
  'activity', 'gauge', 'cog', 'factory', 'hammer',
]

const PRESET_COLORS = [
  '#6366F1', '#0EA5E9', '#F59E0B', '#EF4444', '#10B981',
  '#8B5CF6', '#EC4899', '#F97316', '#14B8A6', '#64748B',
]

function iconFor(name: string): Component {
  return ICON_MAP[name?.toLowerCase()] ?? Construction
}

// ─── Line Types CRUD ──────────────────────────────────────────────────────────

const showAddType   = ref(false)
const editTypeTarget = ref<LineType | null>(null)
const deleteTypeTarget = ref<LineType | null>(null)
const typeForm      = ref({ name: '', icon: 'factory', color: '#6366F1' })
const typeLoading   = ref(false)

function openAddType() {
  typeForm.value = { name: '', icon: 'factory', color: '#6366F1' }
  showAddType.value = true
}

function openEditType(lt: LineType) {
  editTypeTarget.value = lt
  typeForm.value = { name: lt.name, icon: lt.icon, color: lt.color }
}

async function saveAddType() {
  if (!typeForm.value.name.trim()) { toast('Name is required', 'error'); return }
  typeLoading.value = true
  try {
    await linesStore.createLineType(typeForm.value)
    toast(`Line type "${typeForm.value.name}" created!`)
    showAddType.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { typeLoading.value = false }
}

async function saveEditType() {
  if (!editTypeTarget.value) return
  if (!typeForm.value.name.trim()) { toast('Name is required', 'error'); return }
  typeLoading.value = true
  try {
    await linesStore.updateLineType(editTypeTarget.value.id, typeForm.value)
    toast('Line type updated!')
    editTypeTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { typeLoading.value = false }
}

async function doDeleteType() {
  if (!deleteTypeTarget.value) return
  try {
    await linesStore.deleteLineType(deleteTypeTarget.value.id)
    toast('Line type deleted', 'warning')
    deleteTypeTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Lines CRUD ───────────────────────────────────────────────────────────────

const showAddLine      = ref(false)
const addLineTypeId    = ref<string | null>(null)
const editLineTarget   = ref<Line | null>(null)
const deleteLineTarget = ref<Line | null>(null)
const lineForm         = ref({ name: '', icon: 'factory', color: '#6366F1', lineTypeId: null as string | null })
const lineLoading      = ref(false)

const lineTypeOptions = computed(() => [
  { value: '', label: '— Unassigned —' },
  ...linesStore.lineTypes.map(t => ({ value: t.id, label: t.name })),
])

function openAddLine(typeId: string | null = null) {
  addLineTypeId.value = typeId
  lineForm.value = { name: '', icon: 'factory', color: '#6366F1', lineTypeId: typeId }
  showAddLine.value = true
}

function openEditLine(line: Line) {
  editLineTarget.value = line
  lineForm.value = { name: line.name, icon: line.icon, color: line.color, lineTypeId: line.lineTypeId }
}

async function saveAddLine() {
  if (!lineForm.value.name.trim()) { toast('Name is required', 'error'); return }
  lineLoading.value = true
  try {
    await linesStore.createLine({
      name:       lineForm.value.name.trim(),
      icon:       lineForm.value.icon,
      color:      lineForm.value.color,
      lineTypeId: lineForm.value.lineTypeId || null,
    })
    toast(`Line "${lineForm.value.name}" created!`)
    showAddLine.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { lineLoading.value = false }
}

async function saveEditLine() {
  if (!editLineTarget.value) return
  if (!lineForm.value.name.trim()) { toast('Name is required', 'error'); return }
  lineLoading.value = true
  try {
    await linesStore.updateLine(editLineTarget.value.id, {
      name:       lineForm.value.name,
      icon:       lineForm.value.icon,
      color:      lineForm.value.color,
      lineTypeId: lineForm.value.lineTypeId || null,
    })
    toast('Line updated!')
    editLineTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { lineLoading.value = false }
}

async function doDeleteLine() {
  if (!deleteLineTarget.value) return
  try {
    await linesStore.deleteLine(deleteLineTarget.value.id)
    toast('Line deleted', 'warning')
    deleteLineTarget.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Drag-and-drop reorder for line types ────────────────────────────────────

const dragTypeId   = ref<string | null>(null)
const dragOverTypeId = ref<string | null>(null)

function onTypeDragStart(id: string, e: DragEvent) {
  dragTypeId.value = id
  e.dataTransfer!.effectAllowed = 'move'
}

function onTypeDragOver(id: string, e: DragEvent) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  dragOverTypeId.value = id
}

function onTypeDragLeave() {
  dragOverTypeId.value = null
}

async function onTypeDrop(targetId: string) {
  const srcId = dragTypeId.value
  dragTypeId.value    = null
  dragOverTypeId.value = null
  if (!srcId || srcId === targetId) return

  const types  = [...linesStore.linesByType]
  const srcIdx = types.findIndex(t => t.id === srcId)
  const tgtIdx = types.findIndex(t => t.id === targetId)
  if (srcIdx === -1 || tgtIdx === -1) return

  const reordered = [...types]
  const [item]    = reordered.splice(srcIdx, 1)
  reordered.splice(tgtIdx, 0, item)

  try {
    await linesStore.reorderLineTypes(reordered.map(t => t.id))
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Drag-and-drop reorder for lines within a type ───────────────────────────

const dragLineId   = ref<string | null>(null)
const dragOverLineId = ref<string | null>(null)

function onLineDragStart(id: string, e: DragEvent) {
  dragLineId.value = id
  e.dataTransfer!.effectAllowed = 'move'
}

function onLineDragOver(id: string, e: DragEvent) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  dragOverLineId.value = id
}

function onLineDragLeave() {
  dragOverLineId.value = null
}

async function onLineDrop(targetId: string, typeId: string) {
  const srcId = dragLineId.value
  dragLineId.value    = null
  dragOverLineId.value = null
  if (!srcId || srcId === targetId) return

  const group = linesStore.linesByType.find(t => t.id === typeId)
  if (!group) return

  const lines  = [...group.lines]
  const srcIdx = lines.findIndex(l => l.id === srcId)
  const tgtIdx = lines.findIndex(l => l.id === targetId)
  if (srcIdx === -1 || tgtIdx === -1) return

  const reordered = [...lines]
  const [item]    = reordered.splice(srcIdx, 1)
  reordered.splice(tgtIdx, 0, item)

  try {
    // Reorder all lines globally by collecting all IDs in correct order
    const allReordered: string[] = []
    for (const group of linesStore.linesByType) {
      if (group.id === typeId) {
        allReordered.push(...reordered.map(l => l.id))
      } else {
        allReordered.push(...group.lines.map(l => l.id))
      }
    }
    await linesStore.reorderLines(allReordered)
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ─── Shared form component helpers ───────────────────────────────────────────

const formTitle = computed(() => {
  if (showAddType.value) return 'Add Line Type'
  if (editTypeTarget.value) return `Edit Type — ${editTypeTarget.value.name}`
  if (showAddLine.value) return 'Add Line'
  if (editLineTarget.value) return `Edit Line — ${editLineTarget.value.name}`
  return ''
})
</script>

<template>
  <div class="p-8">
    <div class="flex items-start justify-between mb-7">
      <PageHeader
        title="Line Management"
        :subtitle="`${linesStore.lineTypes.length} type(s) · ${linesStore.lines.length} line(s)`"/>
      <AppButton @click="openAddType"><Plus :size="15"/> Add Line Type</AppButton>
    </div>

    <!-- Empty state -->
    <template v-if="linesStore.linesByType.length === 0">
      <AppCard class="text-center py-16">
        <Construction :size="48" class="mx-auto mb-4 text-surface-400"/>
        <h3 class="text-lg font-bold text-slate-100 mb-2">No Line Types Yet</h3>
        <p class="text-sm text-surface-200 mb-5">Create a line type (e.g. Assembly) to start organising your production lines.</p>
        <AppButton @click="openAddType"><Plus :size="15"/> Add Line Type</AppButton>
      </AppCard>
    </template>

    <!-- Line type cards with drag-and-drop -->
    <div class="space-y-6">
      <AppCard v-for="group in linesStore.linesByType" :key="group.id"
        draggable="true"
        @dragstart="onTypeDragStart(group.id, $event)"
        @dragover="onTypeDragOver(group.id, $event)"
        @dragleave="onTypeDragLeave"
        @drop="onTypeDrop(group.id)"
        :class="['transition-all', dragOverTypeId === group.id ? 'ring-2 ring-brand-500/50 opacity-80' : '']">

        <!-- Type header row -->
        <div class="flex items-center gap-3 mb-4">
          <GripVertical :size="16" class="text-surface-500 cursor-grab flex-shrink-0"/>
          <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
               :style="{ background: group.color + '22' }">
            <component :is="iconFor(group.icon)" :size="16" :style="{ color: group.color }"/>
          </div>
          <div class="flex-1">
            <div class="text-sm font-bold text-slate-100">{{ group.name }}</div>
            <div class="text-xs text-surface-300">{{ group.lines.length }} line(s)</div>
          </div>
          <div class="flex items-center gap-2">
            <AppButton size="sm" variant="secondary" @click="openEditType(group)">
              <Pencil :size="13"/>
            </AppButton>
            <AppButton size="sm" variant="danger" @click="deleteTypeTarget = group">
              <Trash2 :size="13"/>
            </AppButton>
            <AppButton size="sm" @click="openAddLine(group.id)">
              <Plus :size="13"/> Line
            </AppButton>
          </div>
        </div>

        <!-- Lines list -->
        <div v-if="group.lines.length > 0" class="space-y-2">
          <div v-for="line in group.lines" :key="line.id"
            draggable="true"
            @dragstart="onLineDragStart(line.id, $event)"
            @dragover="onLineDragOver(line.id, $event)"
            @dragleave="onLineDragLeave"
            @drop="onLineDrop(line.id, group.id)"
            :class="['flex items-center gap-3 bg-surface-800 rounded-xl px-4 py-3 border transition-all cursor-default',
                     dragOverLineId === line.id ? 'border-brand-500/50 ring-1 ring-brand-500/30' : 'border-surface-700']">
            <GripVertical :size="14" class="text-surface-500 cursor-grab flex-shrink-0"/>
            <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                 :style="{ background: line.color + '22' }">
              <component :is="iconFor(line.icon)" :size="14" :style="{ color: line.color }"/>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-semibold text-slate-200 truncate">{{ line.name }}</div>
              <div class="text-xs text-surface-300">{{ line.stationCount }} station(s)</div>
            </div>
            <div class="flex gap-2">
              <AppButton size="sm" variant="secondary" @click="openEditLine(line)">
                <Pencil :size="12"/>
              </AppButton>
              <AppButton size="sm" variant="danger" @click="deleteLineTarget = line">
                <Trash2 :size="12"/>
              </AppButton>
            </div>
          </div>
        </div>

        <div v-else class="text-xs text-surface-400 text-center py-4 border border-dashed border-surface-700 rounded-xl">
          No lines yet — click "+ Line" to add one.
        </div>
      </AppCard>
    </div>

    <!-- ── Add / Edit Line Type Modal ─────────────────────────────────────── -->
    <AppModal :open="showAddType || !!editTypeTarget" :title="formTitle"
      @close="showAddType = false; editTypeTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Name">
          <AppInput v-model="typeForm.name" placeholder="e.g. Assembly"/>
        </FormField>
        <FormField label="Icon">
          <div class="grid grid-cols-8 gap-1.5">
            <button v-for="iconName in AVAILABLE_ICONS" :key="iconName"
              type="button" @click="typeForm.icon = iconName"
              :class="['p-2 rounded-lg transition-all flex items-center justify-center',
                       typeForm.icon === iconName
                         ? 'bg-brand-500/25 border border-brand-500/50 text-brand-400'
                         : 'bg-surface-800 border border-surface-700 text-surface-300 hover:bg-surface-700']"
              :title="iconName">
              <component :is="iconFor(iconName)" :size="15"/>
            </button>
          </div>
        </FormField>
        <FormField label="Color">
          <div class="flex items-center gap-3">
            <input type="color" v-model="typeForm.color"
              class="w-10 h-10 rounded-lg border border-surface-600 bg-surface-800 cursor-pointer p-1"/>
            <div class="flex gap-1.5 flex-wrap">
              <button v-for="c in PRESET_COLORS" :key="c" type="button"
                @click="typeForm.color = c"
                class="w-6 h-6 rounded-full border-2 transition-all"
                :style="{ background: c, borderColor: typeForm.color === c ? '#fff' : 'transparent' }"/>
            </div>
          </div>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAddType = false; editTypeTarget = null">Cancel</AppButton>
        <AppButton :disabled="typeLoading" @click="editTypeTarget ? saveEditType() : saveAddType()">
          {{ typeLoading ? 'Saving…' : (editTypeTarget ? 'Save Changes' : 'Add Type') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Add / Edit Line Modal ──────────────────────────────────────────── -->
    <AppModal :open="showAddLine || !!editLineTarget" :title="formTitle"
      @close="showAddLine = false; editLineTarget = null">
      <div class="space-y-4 mb-5">
        <FormField label="Name">
          <AppInput v-model="lineForm.name" placeholder="e.g. Trim Line"/>
        </FormField>
        <FormField label="Line Type">
          <select v-model="lineForm.lineTypeId"
            class="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500">
            <option v-for="opt in lineTypeOptions" :key="opt.value" :value="opt.value || null">{{ opt.label }}</option>
          </select>
        </FormField>
        <FormField label="Icon">
          <div class="grid grid-cols-8 gap-1.5">
            <button v-for="iconName in AVAILABLE_ICONS" :key="iconName"
              type="button" @click="lineForm.icon = iconName"
              :class="['p-2 rounded-lg transition-all flex items-center justify-center',
                       lineForm.icon === iconName
                         ? 'bg-brand-500/25 border border-brand-500/50 text-brand-400'
                         : 'bg-surface-800 border border-surface-700 text-surface-300 hover:bg-surface-700']"
              :title="iconName">
              <component :is="iconFor(iconName)" :size="15"/>
            </button>
          </div>
        </FormField>
        <FormField label="Color">
          <div class="flex items-center gap-3">
            <input type="color" v-model="lineForm.color"
              class="w-10 h-10 rounded-lg border border-surface-600 bg-surface-800 cursor-pointer p-1"/>
            <div class="flex gap-1.5 flex-wrap">
              <button v-for="c in PRESET_COLORS" :key="c" type="button"
                @click="lineForm.color = c"
                class="w-6 h-6 rounded-full border-2 transition-all"
                :style="{ background: c, borderColor: lineForm.color === c ? '#fff' : 'transparent' }"/>
            </div>
          </div>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAddLine = false; editLineTarget = null">Cancel</AppButton>
        <AppButton :disabled="lineLoading" @click="editLineTarget ? saveEditLine() : saveAddLine()">
          {{ lineLoading ? 'Saving…' : (editLineTarget ? 'Save Changes' : 'Add Line') }}
        </AppButton>
      </div>
    </AppModal>

    <!-- ── Unlinked Lines ─────────────────────────────────────────────────── -->
    <AppCard v-if="linesStore.untypedLines.length > 0" class="mt-6 border-amber-500/30">
      <div class="flex items-center gap-2 mb-4">
        <Construction :size="16" class="text-amber-400 flex-shrink-0"/>
        <h3 class="text-sm font-bold text-amber-300">Unlinked Lines</h3>
        <span class="text-xs text-surface-400 ml-1">— these lines have no type assigned</span>
      </div>
      <div class="space-y-2">
        <div v-for="line in linesStore.untypedLines" :key="line.id"
          class="flex items-center gap-3 bg-surface-800 rounded-xl px-4 py-3 border border-amber-500/20">
          <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
               :style="{ background: line.color + '22' }">
            <component :is="iconFor(line.icon)" :size="14" :style="{ color: line.color }"/>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-slate-200 truncate">{{ line.name }}</div>
            <div class="text-xs text-surface-300">{{ line.stationCount }} station(s) · no type</div>
          </div>
          <AppButton size="sm" variant="secondary" @click="openEditLine(line)">
            <Pencil :size="12"/> Assign Type
          </AppButton>
          <AppButton size="sm" variant="danger" @click="deleteLineTarget = line">
            <Trash2 :size="12"/>
          </AppButton>
        </div>
      </div>
    </AppCard>

    <!-- ── Delete confirmations ───────────────────────────────────────────── -->
    <ConfirmDialog
      :open="!!deleteTypeTarget"
      title="Delete Line Type"
      danger
      label="Delete"
      :message="`Delete type &quot;${deleteTypeTarget?.name}&quot;? All lines in this type will be unlinked.`"
      @close="deleteTypeTarget = null"
      @confirm="doDeleteType"/>

    <ConfirmDialog
      :open="!!deleteLineTarget"
      title="Delete Line"
      danger
      label="Delete"
      :message="`Delete line &quot;${deleteLineTarget?.name}&quot;? This can only be done if the line has no stations.`"
      @close="deleteLineTarget = null"
      @confirm="doDeleteLine"/>
  </div>
</template>
