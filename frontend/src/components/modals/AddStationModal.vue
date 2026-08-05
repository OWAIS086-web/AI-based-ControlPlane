<script setup lang="ts">
import AppModal  from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput  from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'
import { ref } from 'vue'

const emit = defineEmits<{ close: []; confirm: [name: string] }>()

const name = ref('')

function submit() {
  emit('confirm', name.value)
  name.value = ''
}

function close() {
  name.value = ''
  emit('close')
}
</script>

<template>
  <AppModal :open="true" title="Add New Station" @close="close">
    <FormField label="Station Name" class="mb-5">
      <AppInput v-model="name" placeholder="Station 07" @keyup.enter="submit"/>
    </FormField>
    <div class="flex gap-3 justify-end">
      <AppButton variant="secondary" @click="close">Cancel</AppButton>
      <AppButton @click="submit">Add Station</AppButton>
    </div>
  </AppModal>
</template>