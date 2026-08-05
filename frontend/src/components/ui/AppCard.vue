<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  padding?: string
  noPad?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  padding: 'p-5',
  noPad: false,
})
</script>

<template>
  <div :class="cn('bg-surface-900 border border-surface-600 rounded-xl', !noPad && padding, props.class)">
    <slot />
  </div>
</template>
