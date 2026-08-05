<script setup lang="ts">
import { computed } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-bold',
)

interface Props {
  color?: string
  variant?: 'default' | 'dot'
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  color: '#6366F1',
  variant: 'default',
})

const textColor = computed(() => {
  const hex = props.color.replace('#', '')
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#000000' : '#ffffff'
})
</script>

<template>
  <span
    :class="cn(badgeVariants(), props.class)"
    :style="{ background: color, color: textColor }"
  >
    <span v-if="variant === 'dot'" class="w-1.5 h-1.5 rounded-full" :style="{ background: textColor }" />
    <slot />
  </span>
</template>
