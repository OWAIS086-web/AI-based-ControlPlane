<script setup lang="ts">
import type { AIStatus } from '@/stores/aiStatus'

const props = defineProps<{ status: AIStatus; showLabel?: boolean }>()
</script>

<template>
  <!-- idle: render nothing -->
  <template v-if="props.status === 'idle'" />

  <!-- ai_running: pulsing purple-blue ring + label -->
  <span v-else-if="props.status === 'ai_running'"
    class="inline-flex items-center gap-1.5">
    <span class="relative flex h-2.5 w-2.5 flex-shrink-0">
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"/>
      <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-gradient-to-br from-purple-500 to-blue-500"/>
    </span>
    <span v-if="showLabel !== false"
      class="text-[10px] font-semibold tracking-wide bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent uppercase">
      AI Processing
    </span>
  </span>

  <!-- completed: solid green dot -->
  <span v-else-if="props.status === 'completed'"
    class="inline-flex items-center gap-1.5">
    <span class="h-2.5 w-2.5 rounded-full bg-green-500 flex-shrink-0"/>
    <span v-if="showLabel !== false"
      class="text-[10px] font-semibold text-green-400 uppercase tracking-wide">
      Diff Ready
    </span>
  </span>

  <!-- failed: red dot -->
  <span v-else-if="props.status === 'failed'"
    class="inline-flex items-center gap-1.5">
    <span class="h-2.5 w-2.5 rounded-full bg-red-500 flex-shrink-0"/>
    <span v-if="showLabel !== false"
      class="text-[10px] font-semibold text-red-400 uppercase tracking-wide">
      Diff Failed
    </span>
  </span>
</template>
