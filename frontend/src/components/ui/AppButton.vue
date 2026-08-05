<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-vue-next'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'success'
type Size    = 'sm' | 'md' | 'lg'

const buttonVariants = cva(
  'inline-flex items-center justify-center font-semibold rounded-lg border transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        primary:   'bg-brand-500 hover:bg-brand-600 text-white border-transparent',
        secondary: 'bg-surface-700 hover:bg-surface-600 text-slate-300 border-surface-600',
        danger:    'bg-transparent hover:bg-red-950 text-red-400 border-red-900',
        ghost:     'bg-transparent hover:bg-surface-700 text-slate-400 border-transparent',
        success:   'bg-transparent hover:bg-emerald-950 text-emerald-400 border-emerald-900',
      },
      size: {
        sm: 'px-3 py-1.5 text-xs gap-1.5',
        md: 'px-4 py-2 text-sm gap-2',
        lg: 'px-5 py-2.5 text-sm gap-2',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)

interface Props {
  variant?: Variant
  size?: Size
  disabled?: boolean
  loading?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
})
</script>

<template>
  <button
    :disabled="disabled || loading"
    :class="cn(buttonVariants({ variant, size }), props.class)"
  >
    <Loader2 v-if="loading" :size="14" class="animate-spin" />
    <slot />
  </button>
</template>
