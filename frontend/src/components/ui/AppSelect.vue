<script setup lang="ts">
import { computed } from 'vue'
import {
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectPortal,
  SelectContent,
  SelectViewport,
  SelectItem,
  SelectItemText,
  SelectScrollUpButton,
  SelectScrollDownButton,
} from 'radix-vue'
import { ChevronDown, ChevronUp, Check } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

interface Option {
  value: string | number
  label: string
}

interface Props {
  modelValue?: string | number
  options?: Option[]
  placeholder?: string
  class?: string
}

const props = withDefaults(defineProps<Props>(), { options: () => [] })
const emit = defineEmits<{ 'update:modelValue': [value: string | number] }>()

// Radix Select works with strings; we preserve the original type on emit
const stringValue = computed(() => props.modelValue?.toString() ?? '')

function handleUpdate(val: string) {
  const match = props.options.find(o => o.value?.toString() === val)
  emit('update:modelValue', match ? match.value : val)
}
</script>

<template>
  <SelectRoot :model-value="stringValue" @update:model-value="handleUpdate">
    <SelectTrigger
      :class="cn(
        'flex h-9 w-full items-center justify-between rounded-lg border border-surface-600',
        'bg-surface-950 px-3 py-2 text-sm text-slate-100 cursor-pointer',
        'focus:outline-none focus:border-brand-500 transition-colors',
        'data-[placeholder]:text-surface-300',
        props.class
      )"
    >
      <SelectValue :placeholder="placeholder ?? 'Select…'" />
      <ChevronDown :size="14" class="text-surface-300 flex-shrink-0" />
    </SelectTrigger>

    <SelectPortal>
      <SelectContent
        class="relative z-[200] min-w-[8rem] overflow-hidden rounded-lg border border-surface-600 bg-surface-800 shadow-2xl
               data-[state=open]:animate-fade-in"
        position="popper"
        :side-offset="4"
      >
        <SelectScrollUpButton class="flex items-center justify-center h-6 bg-surface-800 text-surface-300 cursor-default">
          <ChevronUp :size="14" />
        </SelectScrollUpButton>

        <SelectViewport class="p-1 max-h-60">
          <SelectItem
            v-for="opt in options.filter(o => String(o.value) !== '')"
            :key="opt.value"
            :value="opt.value.toString()"
            class="relative flex w-full cursor-pointer select-none items-center rounded-md py-2 pl-8 pr-3 text-sm text-slate-200
                   outline-none transition-colors hover:bg-surface-700 focus:bg-surface-700
                   data-[state=checked]:text-brand-400 data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
          >
            <span class="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
              <Check :size="12" class="text-brand-400" v-if="opt.value?.toString() === stringValue" />
            </span>
            <SelectItemText>{{ opt.label }}</SelectItemText>
          </SelectItem>
        </SelectViewport>

        <SelectScrollDownButton class="flex items-center justify-center h-6 bg-surface-800 text-surface-300 cursor-default">
          <ChevronDown :size="14" />
        </SelectScrollDownButton>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
