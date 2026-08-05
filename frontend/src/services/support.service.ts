import { api } from '@/services/api'

export interface BugReportPayload {
  title: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  steps_to_reproduce?: string
  expected_behavior?: string
  actual_behavior?: string
}

export interface FeatureRequestPayload {
  title: string
  description: string
  priority: 'low' | 'medium' | 'high'
  use_case?: string
}

export interface SupportOut {
  success: boolean
  message: string
}

export const supportService = {
  async reportBug(payload: BugReportPayload): Promise<SupportOut> {
    return api.post<SupportOut>('/support/bug', payload)
  },

  async requestFeature(payload: FeatureRequestPayload): Promise<SupportOut> {
    return api.post<SupportOut>('/support/feature', payload)
  },
}