<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogClose,
} from 'radix-vue'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean
  title?: string
  wide?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

function onOpenChange(val: boolean) {
  if (!val) emit('close')
}
</script>

<template>
  <DialogRoot :open="open" @update:open="onOpenChange">
    <DialogPortal>
      <DialogOverlay
        class="fixed inset-0 z-50 bg-black/65 backdrop-blur-sm
               data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out"
      />
      <DialogContent
        :class="cn(
          'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2',
          'bg-surface-800 border border-surface-600 rounded-2xl shadow-2xl',
          'w-full max-h-[88vh] overflow-y-auto focus:outline-none',
          'data-[state=open]:animate-slide-up data-[state=closed]:animate-slide-down',
          props.wide ? 'max-w-2xl' : 'max-w-lg'
        )"
      >
        <div class="flex items-center justify-between p-6 pb-4 border-b border-surface-600">
          <DialogTitle class="text-lg font-bold text-slate-100">{{ title }}</DialogTitle>
          <DialogClose class="text-surface-300 hover:text-slate-100 transition-colors rounded-md focus:outline-none focus:ring-1 focus:ring-ring">
            <X :size="20" />
          </DialogClose>
        </div>
        <div class="p-6">
          <slot />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
