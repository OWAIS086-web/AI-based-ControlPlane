<script setup lang="ts">
type Variant = 'primary' | 'secondary' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface Props {
  variant?: Variant
  size?: Size
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
})
</script>

<template>
  <button
    :disabled="disabled"
    :class="[
      'v-btn',
      `v-btn--${variant}`,
      `v-btn--${size}`,
    ]"
  >
    <slot />
  </button>
</template>

<style scoped>
.v-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  white-space: nowrap;
}

.v-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sizes */
.v-btn--sm { padding: 6px 12px; font-size: 0.8125rem; }
.v-btn--md { padding: 10px 20px; font-size: 0.9rem; }
.v-btn--lg { padding: 12px 28px; font-size: 1rem; }

/* Primary */
.v-btn--primary {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}
.v-btn--primary:hover:not(:disabled) {
  background: #2563eb;
  border-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
}

/* Secondary */
.v-btn--secondary {
  background: white;
  color: #374151;
  border-color: #d1d5db;
}
.v-btn--secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

/* Danger */
.v-btn--danger {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fca5a5;
}
.v-btn--danger:hover:not(:disabled) {
  background: #fecaca;
  border-color: #f87171;
  transform: translateY(-1px);
}
</style>
