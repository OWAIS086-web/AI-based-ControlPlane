<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-vue-next'
const { toasts } = useToast()
const cfg = {
  success: { bg: 'bg-emerald-500', Icon: CheckCircle },
  error:   { bg: 'bg-red-500',     Icon: XCircle },
  warning: { bg: 'bg-amber-500',   Icon: AlertTriangle },
  info:    { bg: 'bg-brand-500',   Icon: Info },
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts" :key="t.id"
          :class="['flex items-center gap-3 px-4 py-3 rounded-xl text-white text-sm font-semibold shadow-2xl pointer-events-auto min-w-[280px] animate-toast-in', cfg[t.type]?.bg || cfg.success.bg]"
        >
          <component :is="cfg[t.type]?.Icon || cfg.success.Icon" :size="18" />
          {{ t.msg }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active { animation: toastIn .3s ease }
.toast-leave-active { transition: opacity .3s, transform .3s }
.toast-leave-to { opacity: 0; transform: translateX(110%) }
@keyframes toastIn { from { transform: translateX(110%); opacity: 0 } to { transform: translateX(0); opacity: 1 } }
</style>
