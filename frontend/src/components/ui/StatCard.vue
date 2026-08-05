<script setup lang="ts">
defineProps({ label: String, value: [String, Number], sub: String, color: String })
</script>
<template>
  <div class="bg-surface-900 border border-surface-600 rounded-xl p-5 relative overflow-hidden">
    <div class="text-3xl font-black font-mono mb-1" :style="{ color }">{{ value }}</div>
    <div class="text-sm font-semibold text-slate-300">{{ label }}</div>
    <div v-if="sub" class="text-xs text-surface-200 mt-0.5">{{ sub }}</div>
    <div class="absolute -top-2 -right-2 opacity-[0.06] text-7xl select-none pointer-events-none">
      <slot name="icon" />
    </div>
  </div>
</template>
