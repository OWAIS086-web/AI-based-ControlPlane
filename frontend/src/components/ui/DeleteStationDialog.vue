<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal  from './AppModal.vue'
import AppButton from './AppButton.vue'
import AppInput  from './AppInput.vue'
import { AlertTriangle } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  stationName: string | undefined
  totalProcsCount: number
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()

const typed = ref('')
watch(() => props.open, v => { if (!v) typed.value = '' })

function close() { emit('close') }
function confirm() { emit('confirm'); emit('close') }
</script>

<template>
  <AppModal :open="open" title="Delete Station" @close="close">
    <!-- Blocked: any processes exist (active or archived) -->
    <template v-if="totalProcsCount > 0">
      <div class="flex gap-3 p-4 bg-amber-500/10 border border-amber-500/25 rounded-xl mb-5">
        <AlertTriangle :size="18" class="text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-amber-300 mb-1">
            Station has {{ totalProcsCount }} process{{ totalProcsCount === 1 ? '' : 'es' }} assigned
          </p>
          <p class="text-xs text-amber-400/80 leading-relaxed">
            All processes (including archived) must be migrated away before this station can be deleted.
          </p>
        </div>
      </div>
      <div class="flex justify-end">
        <AppButton variant="secondary" @click="close">Close</AppButton>
      </div>
    </template>

    <!-- Safe to delete -->
    <template v-else>
      <p class="text-surface-200 text-sm leading-relaxed mb-5">
        Permanently delete <strong class="text-slate-100">{{ stationName }}</strong>? This cannot be undone.
      </p>
      <div class="mb-5">
        <p class="text-surface-300 text-xs mb-2">
          Type <strong class="text-red-400">{{ stationName }}</strong> to confirm:
        </p>
        <AppInput v-model="typed" :placeholder="stationName" />
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="close">Cancel</AppButton>
        <AppButton variant="danger" :disabled="typed !== stationName" @click="confirm">
          Delete Station
        </AppButton>
      </div>
    </template>
  </AppModal>
</template>
