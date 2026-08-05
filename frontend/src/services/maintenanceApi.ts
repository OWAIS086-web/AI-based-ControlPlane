/**
 * Maintenance module API client.
 * Uses separate localStorage keys and base URL — fully independent from the main app.
 */

const BASE = '/api/v1/maintenance'

const ACCESS_KEY  = 'm_access_token'
const REFRESH_KEY = 'm_refresh_token'

let _access:  string | null = localStorage.getItem(ACCESS_KEY)
let _refresh: string | null = localStorage.getItem(REFRESH_KEY)

export function mSetTokens(access: string, refresh: string) {
  _access  = access
  _refresh = refresh
  localStorage.setItem(ACCESS_KEY,  access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function mClearTokens() {
  _access  = null
  _refresh = null
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function mGetAccessToken() { return _access }

export class MApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'MApiError'
  }
}

async function tryRefresh(): Promise<boolean> {
  if (!_refresh) return false
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refreshToken: _refresh }),
    })
    if (!res.ok) { mClearTokens(); return false }
    const data = await res.json()
    _access = data.accessToken
    localStorage.setItem(ACCESS_KEY, data.accessToken)
    return true
  } catch {
    mClearTokens()
    return false
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
    ...(_access ? { Authorization: `Bearer ${_access}` } : {}),
  }

  const res  = await fetch(`${BASE}${path}`, { ...init, headers })
  const body = await res.json().catch(() => ({}))

  if (res.status === 401 && retry) {
    const ok = await tryRefresh()
    if (ok) return request<T>(path, init, false)
    throw new MApiError(401, body.detail || 'Session expired. Please log in again.')
  }

  if (res.status === 204) return undefined as T
  if (!res.ok) throw new MApiError(res.status, body.detail || body.title || 'Request failed')
  return body as T
}

export const mApi = {
  get:    <T>(path: string)                  => request<T>(path),
  post:   <T>(path: string, body?: unknown)  => request<T>(path, { method: 'POST',  body: JSON.stringify(body) }),
  patch:  <T>(path: string, body?: unknown)  => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T = void>(path: string)           => request<T>(path, { method: 'DELETE' }),
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MaintenanceUser {
  id: string
  name: string
  email: string
  role: 'admin' | 'technician'
  status: 'active' | 'inactive'
  createdAt: string
  updatedAt: string
}

export interface FaultRecord {
  id: string
  title: string
  description: string
  location: string | null
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'in_progress' | 'resolved'
  reportedBy: string
  reporterName: string
  assignedTo: string | null
  assigneeName: string | null
  resolvedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface FaultComment {
  id: string
  faultId: string
  userId: string
  authorName: string
  body: string
  createdAt: string
}

export interface FaultListResponse {
  data: FaultRecord[]
  meta: { total: number; page: number; pageSize: number; totalPages: number }
}

// ── Services ──────────────────────────────────────────────────────────────────

export const maintenanceAuthService = {
  login:          (email: string, password: string) =>
    mApi.post<{ accessToken: string; refreshToken: string; expiresIn: number; user: MaintenanceUser }>('/auth/login', { email, password }),
  logout:         () => mApi.post('/auth/logout'),
  changePassword: (currentPassword: string, newPassword: string) =>
    mApi.post('/auth/change-password', { currentPassword, newPassword }),
}

export const maintenanceUserService = {
  me:           ()              => mApi.get<MaintenanceUser>('/users/me'),
  list:         ()              => mApi.get<MaintenanceUser[]>('/users'),
  create:       (body: object)  => mApi.post<MaintenanceUser>('/users', body),
  update:       (id: string, body: object) => mApi.patch<MaintenanceUser>(`/users/${id}`, body),
  setStatus:    (id: string, status: string) => mApi.patch<MaintenanceUser>(`/users/${id}/status`, { status }),
  delete:       (id: string)    => mApi.delete(`/users/${id}`),
}

export const maintenanceFaultService = {
  list:   (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return mApi.get<FaultListResponse>(`/faults${qs}`)
  },
  create: (body: object)           => mApi.post<FaultRecord>('/faults', body),
  get:    (id: string)              => mApi.get<FaultRecord>(`/faults/${id}`),
  update: (id: string, body: object) => mApi.patch<FaultRecord>(`/faults/${id}`, body),
  delete: (id: string)              => mApi.delete(`/faults/${id}`),
  comments: {
    list:   (faultId: string)                         => mApi.get<FaultComment[]>(`/faults/${faultId}/comments`),
    add:    (faultId: string, body: string)            => mApi.post<FaultComment>(`/faults/${faultId}/comments`, { body }),
    delete: (faultId: string, commentId: string)       => mApi.delete(`/faults/${faultId}/comments/${commentId}`),
  },
}
