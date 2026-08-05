<template>
  <div class="flex flex-col sm:flex-row items-center justify-between gap-4 w-full text-sm">
    <!-- Left Side: Per Page & Summary -->
    <div class="flex items-center gap-4 text-slate-400">
      <div class="flex items-center gap-2">
        <span class="text-xs">Rows per page</span>
        <div class="relative">
          <select
            :value="perPage"
            @change="onPerPageChange"
            class="h-8 appearance-none rounded border border-surface-700 bg-surface-900 pl-3 pr-8 text-xs text-surface-100 focus:border-blue-600 focus:outline-none"
          >
            <option v-for="option in perPageOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
          <ChevronDown class="absolute right-2 top-2.5 h-3 w-3 pointer-events-none text-slate-500" />
        </div>
      </div>

      <div class="hidden sm:block text-xs">
        Showing {{ startItem }}-{{ endItem }} of {{ totalItems }}
      </div>
    </div>

    <!-- Right Side: Navigation -->
    <div class="flex items-center gap-1">
      <button
        @click="goToPage(1)"
        :disabled="currentPage === 1"
        class="h-8 w-8 flex items-center justify-center rounded border border-surface-700 bg-surface-800 text-surface-100 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title="First Page"
      >
        <ChevronsLeft class="h-4 w-4" />
      </button>

      <button
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage === 1"
        class="h-8 w-8 flex items-center justify-center rounded border border-surface-700 bg-surface-800 text-surface-100 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title="Previous Page"
      >
        <ChevronLeft class="h-4 w-4" />
      </button>

      <template v-for="page in visiblePages" :key="page">
        <button
          v-if="page !== '...'"
          @click="goToPage(page)"
          class="h-8 min-w-[2rem] px-1 flex items-center justify-center rounded border text-xs transition-colors"
          :class="[
            page === currentPage
              ? 'bg-blue-600 border-blue-600 text-white'
              : 'border-surface-700 bg-surface-800 text-surface-100 hover:bg-surface-700',
          ]"
        >
          {{ page }}
        </button>
        <span v-else class="h-8 w-8 flex items-center justify-center text-slate-500">
          <MoreHorizontal class="h-4 w-4" />
        </span>
      </template>

      <button
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="h-8 w-8 flex items-center justify-center rounded border border-surface-700 bg-surface-800 text-surface-100 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title="Next Page"
      >
        <ChevronRight class="h-4 w-4" />
      </button>

      <button
        @click="goToPage(totalPages)"
        :disabled="currentPage === totalPages"
        class="h-8 w-8 flex items-center justify-center rounded border border-surface-700 bg-surface-800 text-surface-100 hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title="Last Page"
      >
        <ChevronsRight class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ChevronDown,
  MoreHorizontal,
} from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    currentPage: number
    totalPages: number
    totalItems: number
    perPage: number
    perPageOptions?: number[]
  }>(),
  {
    perPageOptions: () => [10, 20, 50, 100],
  },
)

const emit = defineEmits<{
  'update:page': [page: number]
  'update:perPage': [perPage: number]
}>()

const startItem = computed(() => {
  if (props.totalItems === 0) return 0
  return (props.currentPage - 1) * props.perPage + 1
})

const endItem = computed(() => {
  return Math.min(props.currentPage * props.perPage, props.totalItems)
})

const onPerPageChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('update:perPage', parseInt(target.value))
  emit('update:page', 1)
}

const goToPage = (page: number | string) => {
  if (typeof page === 'string') return
  if (page >= 1 && page <= props.totalPages) {
    emit('update:page', page)
  }
}

const visiblePages = computed(() => {
  const pages: (number | string)[] = []
  const { currentPage, totalPages } = props

  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (currentPage > 3) pages.push('...')
    const start = Math.max(2, currentPage - 1)
    const end = Math.min(totalPages - 1, currentPage + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (currentPage < totalPages - 2) pages.push('...')
    pages.push(totalPages)
  }
  return pages
})
</script>
