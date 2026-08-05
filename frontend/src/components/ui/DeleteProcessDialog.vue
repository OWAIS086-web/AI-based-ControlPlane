<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal  from './AppModal.vue'
import AppButton from './AppButton.vue'
import AppInput  from './AppInput.vue'
import { AlertTriangle } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  processName: string | undefined
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
  <AppModal :open="open" title="Delete Process" @close="close">
    <div class="flex gap-3 p-4 bg-red-500/10 border border-red-500/25 rounded-xl mb-5">
      <AlertTriangle :size="18" class="text-red-400 shrink-0 mt-0.5" />
      <div>
        <p class="text-sm font-semibold text-red-300 mb-1">This action is permanent</p>
        <p class="text-xs text-red-400/80 leading-relaxed">
          Deleting <strong class="text-red-300">{{ processName }}</strong> will permanently remove it and all its control plan versions. This cannot be undone.
        </p>
      </div>
    </div>
    <div class="mb-5">
      <p class="text-surface-300 text-xs mb-2">
        Type <strong class="text-red-400">confirm</strong> to proceed:
      </p>
      <AppInput v-model="typed" placeholder="confirm" />
    </div>
    <div class="flex gap-3 justify-end">
      <AppButton variant="secondary" @click="close">Cancel</AppButton>
      <AppButton variant="danger" :disabled="typed !== 'confirm'" @click="confirm">
        Delete Process
      </AppButton>
    </div>
  </AppModal>
</template>
