<script setup lang="ts">
defineProps({ label: String, required: Boolean })
</script>
<template>
  <div>
    <label class="block text-[11px] font-bold text-surface-200 uppercase tracking-widest mb-1.5">
      {{ label }}<span v-if="required" class="text-red-400 ml-0.5">*</span>
    </label>
    <slot />
  </div>
</template>
