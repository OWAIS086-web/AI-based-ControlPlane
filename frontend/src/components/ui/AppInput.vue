<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  modelValue?: string | number
  placeholder?: string
  type?: string
  class?: string
}

const props = withDefaults(defineProps<Props>(), { type: 'text' })
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <input
    :value="modelValue"
    :type="type"
    :placeholder="placeholder"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    :class="cn(
      'flex h-9 w-full rounded-lg border border-input bg-surface-950 px-3 py-2 text-sm text-slate-100',
      'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
      'border-surface-600 focus:border-brand-500 transition-colors',
      props.class
    )"
  />
</template>
