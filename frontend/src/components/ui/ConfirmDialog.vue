<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal from './AppModal.vue'
import AppButton from './AppButton.vue'
import AppInput from './AppInput.vue'

const props = defineProps({
  open: Boolean, title: String, message: String,
  label: { default: 'Confirm' }, danger: Boolean,
  requireTyping: String,
})
const emit = defineEmits(['close', 'confirm'])
const typed = ref('')
watch(() => props.open, v => { if (!v) typed.value = '' })
const canConfirm = () => props.requireTyping ? typed.value === props.requireTyping : true
</script>

<template>
  <AppModal :open="open" :title="title" @close="$emit('close')">
    <p class="text-surface-200 text-sm leading-relaxed mb-5">{{ message }}</p>
    <div v-if="requireTyping" class="mb-5">
      <p class="text-surface-300 text-xs mb-2">
        Type <strong class="text-red-400">{{ requireTyping }}</strong> to confirm:
      </p>
      <AppInput v-model="typed" :placeholder="requireTyping" />
    </div>
    <div class="flex gap-3 justify-end">
      <AppButton variant="secondary" @click="$emit('close')">Cancel</AppButton>
      <AppButton :variant="danger ? 'danger' : 'primary'" :disabled="!canConfirm()"
        @click="canConfirm() && ($emit('confirm'), $emit('close'))">
        {{ label }}
      </AppButton>
    </div>
  </AppModal>
</template>
