import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { carModelsService } from '@/services/carModels.service'
import type { ApiCarModel } from '@/services/carModels.service'

export type { ApiCarModel as CarModel }

export const useCarModelsStore = defineStore('carModels', () => {
  const carModels = ref<ApiCarModel[]>([])

  const activeCarModels = computed(() => carModels.value.filter(m => m.status === 'active'))

  async function fetchCarModels(): Promise<void> {
    const res = await carModelsService.list({ limit: 100 })
    carModels.value = res.data
  }

  async function addCarModel(name: string, code: string, color: string): Promise<void> {
    const model = await carModelsService.create({ name, code, color })
    carModels.value.push(model)
  }

  async function setCarModelStatus(id: string, status: 'active' | 'archived'): Promise<void> {
    const updated = await carModelsService.setStatus(id, { status })
    carModels.value = carModels.value.map(m => m.id === id ? updated : m)
  }

  async function editCarModel(id: string, name: string, code: string, color: string): Promise<void> {
    const updated = await carModelsService.update(id, { name, code, color })
    carModels.value = carModels.value.map(m => m.id === id ? updated : m)
  }

  return { carModels, activeCarModels, fetchCarModels, addCarModel, setCarModelStatus, editCarModel }
})
