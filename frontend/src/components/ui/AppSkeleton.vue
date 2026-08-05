<script setup lang="ts">
defineProps<{
  height?: string   // e.g. 'h-4', 'h-8'
  width?:  string   // e.g. 'w-full', 'w-32'
  rounded?: string  // e.g. 'rounded', 'rounded-xl', 'rounded-full'
}>()
</script>

<template>
  <div :class="[
    'animate-pulse bg-surface-700/60 dark:bg-surface-700',
    height  ?? 'h-4',
    width   ?? 'w-full',
    rounded ?? 'rounded-lg',
  ]"/>
</template>
