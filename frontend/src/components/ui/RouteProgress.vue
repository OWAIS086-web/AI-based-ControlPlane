<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const visible  = ref(false)
const progress = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const router = useRouter()

router.beforeEach(() => {
  progress.value = 0
  visible.value  = true
  if (timer) clearInterval(timer)
  // Fake-advance to 85% while the page loads
  timer = setInterval(() => {
    if (progress.value < 85) progress.value += (85 - progress.value) * 0.12
  }, 60)
})

router.afterEach(() => {
  if (timer) { clearInterval(timer); timer = null }
  progress.value = 100
  setTimeout(() => { visible.value = false; progress.value = 0 }, 300)
})
</script>

<template>
  <Transition name="progress">
    <div v-if="visible"
      class="fixed top-0 left-0 right-0 z-[9999] h-[2px] pointer-events-none">
      <div
        class="h-full bg-brand-500 transition-all duration-200 ease-out shadow-[0_0_6px_0px] shadow-brand-500/60"
        :style="{ width: progress + '%' }"
      />
    </div>
  </Transition>
</template>

<style scoped>
.progress-enter-active, .progress-leave-active { transition: opacity 0.3s; }
.progress-enter-from, .progress-leave-to { opacity: 0; }
</style>
