import { api } from '@/services/api'

export interface SystemConfig {
  cardDisplayMode: 'name' | 'filename'
}

export interface SystemConfigUpdate {
  cardDisplayMode?: 'name' | 'filename'
}

export const configService = {
  async get(): Promise<SystemConfig> {
    return api.get<SystemConfig>('/config')
  },

  async update(payload: SystemConfigUpdate): Promise<SystemConfig> {
    return api.patch<SystemConfig>('/config', payload)
  },
}
