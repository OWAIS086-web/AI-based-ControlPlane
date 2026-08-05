<script setup lang="ts">
import { AvatarRoot, AvatarFallback } from 'radix-vue'
import { cn } from '@/lib/utils'

interface Props {
  initials?: string
  size?: 'sm' | 'md' | 'lg'
  class?: string
}

const props = withDefaults(defineProps<Props>(), { size: 'md' })

const sizes = {
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-base',
}
</script>

<template>
  <AvatarRoot
    :class="cn(
      'relative flex shrink-0 overflow-hidden rounded-full',
      'bg-gradient-to-br from-brand-500 to-purple-500',
      sizes[size],
      props.class
    )"
  >
    <AvatarFallback
      class="flex h-full w-full items-center justify-center font-bold text-white"
    >
      {{ initials }}
    </AvatarFallback>
  </AvatarRoot>
</template>
