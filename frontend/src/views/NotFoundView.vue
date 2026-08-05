<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ROUTES } from '@/constants/routeConstant'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import { Home, ArrowLeft, AlertOctagon } from 'lucide-vue-next'

const router = useRouter()
const auth   = useAuthStore()



function goHome() {
  if (auth.isPM) {
    router.push({ name: ROUTES.dashboardView.name })
  } else {
    router.push({ name: ROUTES.assemblyLineView.name })
  }
}
</script>

<template>
  <div class="p-8 flex flex-col min-h-full">
    <PageHeader title="Not Found" subtitle="This page doesn't exist" />

    <div class="flex-1 flex flex-col items-center justify-center">

      <!-- Error code block -->
      <div class="relative select-none mb-8">
        <!-- Background glow -->
        <div class="absolute inset-0 blur-3xl opacity-20 rounded-full"
             style="background: radial-gradient(ellipse, #6366F1 0%, transparent 70%)" />

        <!-- 404 -->
        <div class="relative text-[10rem] font-black leading-none tracking-tighter tabular-nums"
             style="color: #1e2130; -webkit-text-stroke: 1.5px #6366F1; text-shadow: 0 0 40px #6366F122">
          404
        </div>

        <!-- Scanline overlay -->
        <div class="absolute inset-0 pointer-events-none scanlines rounded" />
      </div>

      <!-- Icon + message card -->
      <div class="w-full max-w-md bg-surface-800 border border-surface-700 rounded-xl p-6 mb-6 flex gap-4 items-start">
        <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
             style="background: #EF444422">
          <AlertOctagon :size="20" style="color: #EF4444" />
        </div>
        <div>
          <div class="text-sm font-bold text-slate-100 mb-1">Station not found</div>
          <div class="text-xs text-surface-200 leading-relaxed">
            The route you're looking for doesn't exist on this assembly line.
            It may have been moved, removed, or you may not have access.
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button @click="router.back()"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-surface-200 bg-surface-800 border border-surface-700 hover:bg-surface-700 hover:text-slate-100 transition-all">
          <ArrowLeft :size="15" />
          Go Back
        </button>
        <button @click="goHome"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all"
          style="background: #6366F1; box-shadow: 0 0 20px #6366F133">
          <Home :size="15" />
          {{ auth.isPM ? 'Dashboard' : 'My Line' }}
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* CRT scanlines */
.scanlines {
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 3px,
    rgba(0, 0, 0, 0.08) 3px,
    rgba(0, 0, 0, 0.08) 4px
  );
}
</style>