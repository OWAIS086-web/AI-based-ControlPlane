const BASE_URL = '/api/v1'

let _accessToken: string | null = localStorage.getItem('cp_access_token')
let _refreshToken: string | null = localStorage.getItem('cp_refresh_token')

export function setTokens(access: string, refresh: string) {
  _accessToken = access
  _refreshToken = refresh
  localStorage.setItem('cp_access_token', access)
  localStorage.setItem('cp_refresh_token', refresh)
}

export function clearTokens() {
  _accessToken = null
  _refreshToken = null
  localStorage.removeItem('cp_access_token')
  localStorage.removeItem('cp_refresh_token')
}

export function getAccessToken() {
  return _accessToken
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function tryRefresh(): Promise<boolean> {
  if (!_refreshToken) return false
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken: _refreshToken }),
    })
    if (!res.ok) { clearTokens(); return false }
    const data = await res.json()
    _accessToken = data.accessToken
    localStorage.setItem('cp_access_token', data.accessToken)
    return true
  } catch {
    clearTokens()
    return false
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const isFormData = init.body instanceof FormData
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(init.headers as Record<string, string>),
    ...(_accessToken ? { Authorization: `Bearer ${_accessToken}` } : {}),
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  const body = await res.json().catch(() => ({}))

  if (res.status === 401 && retry) {
    const refreshed = await tryRefresh()
    if (refreshed) return request<T>(path, init, false)
      console.log('Unauthorized, and refresh failed', body)
    throw new ApiError(401, body.detail || body.title || 'Session expired. Please log in again.')
  }

  if (res.status === 204) return undefined as T

  if (!res.ok) throw new ApiError(res.status, body.detail || body.title || 'Request failed')
  return body as T
}

async function requestBlob(path: string, init: RequestInit = {}, retry = true): Promise<Blob> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
    ...(_accessToken ? { Authorization: `Bearer ${_accessToken}` } : {}),
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  if (res.status === 401 && retry) {
    const refreshed = await tryRefresh()
    if (refreshed) return requestBlob(path, init, false)
    const errBody = await res.json().catch(() => ({}))
    throw new ApiError(401, errBody.detail || errBody.title || 'Session expired. Please log in again.')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail || body.title || 'Request failed')
  }

  return res.blob()
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    limit: number
    totalPages: number
  }
}

/**
 * Downloads a binary resource via XHR so that download progress can be tracked.
 * `onProgress` receives 0–100 while the server reports Content-Length, or -1 when
 * the response is chunked / Content-Length is absent (indeterminate progress).
 */
export function blobWithProgress(
  path: string,
  onProgress: (pct: number) => void,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.responseType = 'blob'
    xhr.open('GET', `${BASE_URL}${path}`)
    if (_accessToken) xhr.setRequestHeader('Authorization', `Bearer ${_accessToken}`)

    xhr.onprogress = (e: ProgressEvent) => {
      onProgress(e.lengthComputable ? Math.round((e.loaded / e.total) * 100) : -1)
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as Blob)
      } else {
        reject(new ApiError(xhr.status, 'Download failed'))
      }
    }

    xhr.onerror = () => reject(new Error('Network failure'))
    xhr.onabort = () => reject(new Error('Download cancelled'))
    xhr.send()
  })
}

export const api = {
  get:    <T>(path: string)                 => request<T>(path),
  post:   <T>(path: string, body?: unknown, noRetry = false) => request<T>(path, {
    method: 'POST',
    body: body instanceof FormData ? body : JSON.stringify(body),
  }, !noRetry),
  patch:  <T>(path: string, body?: unknown) => request<T>(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),
  delete: <T = void>(path: string)          => request<T>(path, { method: 'DELETE' }),
  blob:   (path: string)                    => requestBlob(path),
}