<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCarModelsStore } from '@/stores/carModels'
import { useToast } from '@/composables/useToast'
import AppCard      from '@/components/ui/AppCard.vue'
import AppButton    from '@/components/ui/AppButton.vue'
import AppBadge     from '@/components/ui/AppBadge.vue'
import AppModal     from '@/components/ui/AppModal.vue'
import AppInput     from '@/components/ui/AppInput.vue'
import FormField    from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import PageHeader    from '@/components/ui/PageHeader.vue'
import SkeletonCards from '@/components/ui/SkeletonCards.vue'
import { Plus, Archive, RotateCcw, Pencil } from 'lucide-vue-next'
import type { CarModel } from '@/stores/carModels'

const auth    = useAuthStore()
const cmStore = useCarModelsStore()
const { toast } = useToast()

const loading = ref(true)
onMounted(async () => {
  try { await cmStore.fetchCarModels() } finally { loading.value = false }
})

const tab        = ref('active')
const showAdd    = ref(false)
const archiveTgt = ref<CarModel | null>(null)
const form       = ref({ name:'', code:'', color:'#6366F1' })
const editTgt    = ref<CarModel | null>(null)
const editForm   = ref({ name:'', code:'', color:'' })

const active   = computed(() => cmStore.carModels.filter(m => m.status === 'active'))
const archived = computed(() => cmStore.carModels.filter(m => m.status === 'archived'))
const list     = computed(() => tab.value === 'active' ? active.value : archived.value)

async function addModel() {
  if (!form.value.name || !form.value.code) { toast('Name and code required', 'error'); return }
  try {
    await cmStore.addCarModel(form.value.name, form.value.code, form.value.color)
    toast(`"${form.value.name}" added!`)
    form.value = { name:'', code:'', color:'#6366F1' }; showAdd.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

function openEdit(m: CarModel) {
  editTgt.value = m
  editForm.value = { name: m.name, code: m.code, color: m.color }
}

async function saveEdit() {
  if (!editTgt.value) return
  if (!editForm.value.name || !editForm.value.code) { toast('Name and code are required', 'error'); return }
  try {
    await cmStore.editCarModel(editTgt.value.id, editForm.value.name, editForm.value.code, editForm.value.color)
    toast(`"${editForm.value.name}" updated!`)
    editTgt.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function restore(m: CarModel) {
  try {
    await cmStore.setCarModelStatus(m.id, 'active')
    toast(`"${m.name}" restored!`)
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function doArchive() {
  if (!archiveTgt.value) return
  try {
    await cmStore.setCarModelStatus(archiveTgt.value.id, 'archived')
    toast('Archived', 'warning')
    archiveTgt.value = null
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}
</script>

<template>
  <div class="p-8">
    <div class="flex items-start justify-between mb-7">
      <PageHeader title="Car Models" :subtitle="`${active.length} active · ${archived.length} archived`"/>
      <AppButton v-if="auth.isPM" @click="showAdd = true"><Plus :size="15"/> Add Model</AppButton>
    </div>

    <div class="flex gap-2 mb-5">
      <button v-for="t in ['active','archived']" :key="t" @click="tab = t"
        :class="['px-5 py-2 rounded-full text-sm font-bold transition-all capitalize',
                 tab === t ? 'bg-brand-500 text-white' : 'bg-surface-800 text-surface-200 hover:bg-surface-700']">
        {{ t }} ({{ t === 'active' ? active.length : archived.length }})
      </button>
    </div>

    <div v-if="tab === 'archived' && archived.length" class="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/25 rounded-xl mb-5 text-xs text-amber-300">
      <Archive :size="14"/> Showing archived models.
    </div>

    <SkeletonCards v-if="loading" :count="8" cols="grid-cols-2 md:grid-cols-3 lg:grid-cols-4"/>
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div v-for="m in list" :key="m.id"
           :class="['bg-surface-900 border border-surface-600 rounded-xl p-5 relative overflow-hidden transition-opacity', m.status==='archived'?'opacity-75':'']">
        <div class="absolute top-0 left-0 right-0 h-0.5" :style="{ background: m.status==='archived' ? '#475569' : m.color }"/>
        <div class="flex justify-between items-start mb-3">
          <div>
            <div :class="['text-base font-black', m.status==='archived' ? 'text-slate-400' : 'text-slate-100']">{{ m.name }}</div>
            <div class="text-xs font-mono text-surface-300 mt-0.5">{{ m.code }}</div>
          </div>
          <AppBadge :color="m.status==='active'?'#10B981':'#F59E0B'">{{ m.status }}</AppBadge>
        </div>
        <div v-if="auth.isPM" class="flex gap-2 mt-1">
          <AppButton class="flex-1 justify-center" variant="secondary" size="sm" @click="openEdit(m)">
            <Pencil :size="13"/> Edit
          </AppButton>
          <AppButton class="flex-1 justify-center" :variant="m.status==='active' ? 'danger' : 'success'" size="sm"
            @click="m.status==='active' ? archiveTgt=m : restore(m)">
            <Archive v-if="m.status==='active'" :size="13"/> <RotateCcw v-else :size="13"/>
            {{ m.status === 'active' ? 'Archive' : 'Restore' }}
          </AppButton>
        </div>
      </div>
    </div>

    <AppModal :open="showAdd" title="Add Car Model" @close="showAdd=false">
      <div class="space-y-4 mb-5">
        <FormField label="Model Name"><AppInput v-model="form.name" placeholder="Corolla 2025"/></FormField>
        <FormField label="Model Code"><AppInput v-model="form.code" placeholder="COR25"/></FormField>
        <FormField label="Color">
          <input type="color" v-model="form.color" class="w-full h-10 rounded-lg border border-surface-600 bg-surface-950 cursor-pointer p-1"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAdd=false">Cancel</AppButton>
        <AppButton @click="addModel">Add Model</AppButton>
      </div>
    </AppModal>

    <AppModal :open="!!editTgt" :title="`Edit — ${editTgt?.name}`" @close="editTgt=null">
      <div class="space-y-4 mb-5">
        <FormField label="Model Name"><AppInput v-model="editForm.name" placeholder="Corolla 2025"/></FormField>
        <FormField label="Model Code"><AppInput v-model="editForm.code" placeholder="COR25"/></FormField>
        <FormField label="Color">
          <input type="color" v-model="editForm.color" class="w-full h-10 rounded-lg border border-surface-600 bg-surface-950 cursor-pointer p-1"/>
        </FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="editTgt=null">Cancel</AppButton>
        <AppButton @click="saveEdit">Save Changes</AppButton>
      </div>
    </AppModal>

    <ConfirmDialog :open="!!archiveTgt" title="Archive Car Model" danger label="Archive"
      :message="`Archive &quot;${archiveTgt?.name}&quot;? Historical data will be preserved.`"
      @close="archiveTgt=null" @confirm="doArchive"/>
  </div>
</template>
