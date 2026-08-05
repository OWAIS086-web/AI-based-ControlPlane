<script setup lang="ts">
defineProps({ title: String, subtitle: String })
</script>
<template>
  <div class="mb-7">
    <h1 class="text-2xl font-black text-slate-100 tracking-tight">{{ title }}</h1>
    <p v-if="subtitle" class="text-sm text-surface-200 mt-1">{{ subtitle }}</p>
  </div>
</template>
