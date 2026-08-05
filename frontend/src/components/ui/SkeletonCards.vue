<script setup lang="ts">
defineProps<{ count?: number; cols?: string }>()
</script>

<template>
  <div :class="['grid gap-4', cols ?? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4']">
    <div v-for="i in (count ?? 8)" :key="i"
      class="bg-surface-800 rounded-xl p-4 border border-surface-700 space-y-3">
      <div class="flex justify-between items-start">
        <div class="animate-pulse bg-surface-700/60 rounded h-3.5 w-2/3"/>
        <div class="animate-pulse bg-surface-700/40 rounded h-5 w-12"/>
      </div>
      <div class="animate-pulse bg-surface-700/40 rounded h-2.5 w-1/2"/>
      <div class="animate-pulse bg-surface-700/40 rounded h-2.5 w-1/3"/>
      <div class="flex gap-2 pt-1">
        <div class="animate-pulse bg-surface-700/60 rounded-lg h-7 flex-1"/>
        <div class="animate-pulse bg-surface-700/40 rounded-lg h-7 w-10"/>
      </div>
    </div>
  </div>
</template>
