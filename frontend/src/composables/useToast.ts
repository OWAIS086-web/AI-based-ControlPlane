import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  msg: string
  type: ToastType
}

const toasts = ref<Toast[]>([])

export function useToast() {
  function toast(msg: string, type: ToastType = 'success') {
    const id = Date.now()
    toasts.value.push({ id, msg, type })
    setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 3800)
  }
  return { toast, toasts }
}
