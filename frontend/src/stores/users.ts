import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usersService } from '@/services/users.service'
import { linesService } from '@/services/lines.service'
import type { ApiUser } from '@/services/auth.service'

export const useUsersStore = defineStore('users', () => {
  const users        = ref<ApiUser[]>([])
  const lineManagers = ref<Record<string, string | null>>({})

  const lineManagerUsers = computed(() =>
    users.value.filter(u => u.role === 'line_manager' && u.status === 'active'),
  )

  async function fetchUsers(): Promise<void> {
    const res = await usersService.list({ limit: 100 })
    users.value = res.data
  }

  async function fetchLineManagers(): Promise<void> {
    const lines = await linesService.list()
    const map: Record<string, string | null> = {}
    for (const l of lines) map[l.id] = l.managerId ?? null
    lineManagers.value = map
  }

  async function addUser(
    name: string,
    email: string,
    role: ApiUser['role'],
  ): Promise<void> {
    const user = await usersService.create({ name, email, role, password: 'changeme123' })
    users.value.push(user)
  }

  async function toggleUserStatus(id: string): Promise<void> {
    const user = users.value.find(u => u.id === id)
    if (!user) return
    const next = user.status === 'active' ? 'inactive' : 'active'
    const updated = await usersService.setStatus(id, { status: next })
    users.value = users.value.map(u => u.id === id ? updated : u)
  }

  async function deleteUser(id: string): Promise<void> {
    await usersService.remove(id)
    users.value = users.value.filter(u => u.id !== id)
  }

  async function setLineManager(lineId: string, userId: string | null): Promise<void> {
    await linesService.assignManager(lineId, { managerId: userId })
    lineManagers.value = { ...lineManagers.value, [lineId]: userId }
  }

  return {
    users, lineManagers, lineManagerUsers,
    fetchUsers, fetchLineManagers,
    addUser, toggleUserStatus, deleteUser, setLineManager,
  }
})
