export type MaintenanceUserRole   = 'admin' | 'technician'
export type MaintenanceUserStatus = 'active' | 'inactive'
export type FaultSeverity         = 'low' | 'medium' | 'high' | 'critical'
export type FaultStatus           = 'open' | 'in_progress' | 'resolved'

export interface MaintenanceUser {
  id: string
  name: string
  email: string
  role: MaintenanceUserRole
  status: MaintenanceUserStatus
  createdAt: string
}

export interface FaultRecord {
  id: string
  title: string
  description: string
  location: string | null
  severity: FaultSeverity
  status: FaultStatus
  reportedBy: string
  reporterName: string
  assignedTo: string | null
  resolvedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface FaultComment {
  id: string
  faultId: string
  userId: string
  userName: string
  body: string
  createdAt: string
}

export interface FaultListResponse {
  data: FaultRecord[]
  meta: {
    total: number
    page: number
    pageSize: number
    totalPages: number
  }
}

export interface FaultFilter {
  page?: number
  page_size?: number
  status?: FaultStatus | ''
  severity?: FaultSeverity | ''
}

export interface CreateFaultBody {
  title: string
  description: string
  location?: string
  severity: FaultSeverity
}

export interface UpdateFaultBody {
  title?: string
  description?: string
  location?: string
  severity?: FaultSeverity
  status?: FaultStatus
  assigned_to?: string
}

export interface MaintenanceDashboardStats {
  totalFaults: number
  openFaults: number
  inProgressFaults: number
  resolvedFaults: number
  criticalFaults: number
  faultsBySeverity: Record<string, number>
  faultsByStatus: Record<string, number>
  faultsByLocation: Record<string, number>
  faultsByWeek: Record<string, number>
  resolutionRateBySeverity: Record<string, { total: number; resolved: number; rate: number }>
  recentFaults: FaultRecord[]
  allFaults: FaultRecord[]
}
