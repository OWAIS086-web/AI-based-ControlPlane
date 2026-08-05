import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mSetTokens, mClearTokens, mGetAccessToken, maintenanceAuthService, type MaintenanceUser } from '@/services/maintenanceApi'

const USER_KEY = 'm_user'

function persist(user: MaintenanceUser)    { localStorage.setItem(USER_KEY, JSON.stringify(user)) }
function restore(): MaintenanceUser | null {
  try { return JSON.parse(localStorage.getItem(USER_KEY) ?? 'null') } catch { return null }
}
function remove() { localStorage.removeItem(USER_KEY) }

export const useMaintenanceAuthStore = defineStore('maintenanceAuth', () => {
  const currentUser = ref<MaintenanceUser | null>(null)

  const isAdmin      = computed(() => currentUser.value?.role === 'admin')
  const isTechnician = computed(() => currentUser.value?.role === 'technician')
  const isLoggedIn   = computed(() => !!currentUser.value && !!mGetAccessToken())

  async function login(email: string, password: string): Promise<string | null> {
    try {
      const data = await maintenanceAuthService.login(email, password)
      mSetTokens(data.accessToken, data.refreshToken)
      currentUser.value = data.user
      persist(data.user)
      return null
    } catch (err: any) {
      return err?.message ?? 'Invalid credentials'
    }
  }

  function restoreSession() {
    if (!mGetAccessToken()) return
    const stored = restore()
    if (stored) currentUser.value = stored
  }

  async function logout(): Promise<void> {
    try { await maintenanceAuthService.logout() } catch { /* ignore */ }
    mClearTokens()
    remove()
    currentUser.value = null
  }

  return { currentUser, isAdmin, isTechnician, isLoggedIn, login, logout, restoreSession }
})
