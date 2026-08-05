import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configService } from '@/services/config.service'

export const useConfigStore = defineStore('config', () => {
  const cardDisplayMode = ref<'name' | 'filename'>('name')

  async function fetchConfig(): Promise<void> {
    const cfg = await configService.get()
    cardDisplayMode.value = cfg.cardDisplayMode
  }

  async function setCardDisplayMode(mode: 'name' | 'filename'): Promise<void> {
    const cfg = await configService.update({ cardDisplayMode: mode })
    cardDisplayMode.value = cfg.cardDisplayMode
  }

  return { cardDisplayMode, fetchConfig, setCardDisplayMode }
})
