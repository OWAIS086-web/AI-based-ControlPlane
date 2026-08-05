export const ROLES = {
  lineManager:    'line_manager',
  processManager: 'process_manager',
} as const

export type Role = (typeof ROLES)[keyof typeof ROLES]