<script setup lang="ts">
defineProps<{ rows?: number; cols?: number }>()
</script>

<template>
  <div class="w-full">
    <!-- header -->
    <div class="flex gap-4 px-4 py-3 border-b border-surface-700 mb-1">
      <div v-for="i in (cols ?? 4)" :key="i"
        class="animate-pulse bg-surface-700/60 rounded h-3"
        :class="i === 1 ? 'w-1/4' : i === (cols ?? 4) ? 'w-16 ml-auto' : 'flex-1'"/>
    </div>
    <!-- rows -->
    <div v-for="r in (rows ?? 6)" :key="r"
      class="flex gap-4 items-center px-4 py-3.5 border-b border-surface-700/50">
      <div class="animate-pulse bg-surface-700/60 rounded h-3 w-1/4"/>
      <div v-for="i in ((cols ?? 4) - 2)" :key="i"
        class="animate-pulse bg-surface-700/40 rounded h-3 flex-1"/>
      <div class="animate-pulse bg-surface-700/60 rounded h-6 w-16 ml-auto"/>
    </div>
  </div>
</template>
