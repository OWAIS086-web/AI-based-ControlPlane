import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { setTokens, clearTokens, getAccessToken } from '@/services/api'
import { authService } from '@/services/auth.service'
import type { ApiUser } from '@/services/auth.service'

export type { ApiUser as User }

const USER_KEY           = 'cp_user'
const ASSIGNED_LINES_KEY = 'cp_assigned_lines'

function persistUser(user: ApiUser)    { localStorage.setItem(USER_KEY, JSON.stringify(user)) }
function restoreUser(): ApiUser | null {
  try { return JSON.parse(localStorage.getItem(USER_KEY) ?? 'null') } catch { return null }
}
function removeUser()          { localStorage.removeItem(USER_KEY) }
function removeAssignedLines() { localStorage.removeItem(ASSIGNED_LINES_KEY) }

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<ApiUser | null>(null)

  const isPM = computed(() => currentUser.value?.role === 'process_manager')
  const isLM = computed(() => currentUser.value?.role === 'line_manager')

  async function login(email: string, password: string): Promise<string | null> {
    try {
      const data = await authService.login({ email, password })
      setTokens(data.accessToken, data.refreshToken)
      currentUser.value = data.user
      persistUser(data.user)
      return null
    } catch (err: any) {
      console.log(err)
      return err?.detail ?? err?.message ?? 'Invalid credentials'
    }
  }

  // Backend has no /me endpoint — restore user from localStorage.
  // Tokens are already validated by the router guard; if the access token
  // is expired the api client will attempt a silent refresh automatically.
  async function fetchMe(): Promise<void> {
    if (!getAccessToken()) return
    const stored = restoreUser()
    if (stored) currentUser.value = stored
  }

  async function logout(): Promise<void> {
    try { await authService.logout() } catch { /* ignore */ }
    clearTokens()
    removeUser()
    removeAssignedLines()
    currentUser.value = null
  }

  return { currentUser, isPM, isLM, login, logout, fetchMe }
})