<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { maintenanceUserService, type MaintenanceUser } from '@/services/maintenanceApi'
import { useMaintenanceAuthStore } from '@/stores/maintenanceAuth'
import { useToast } from '@/composables/useToast'

const auth       = useMaintenanceAuthStore()
const { toast }  = useToast()

const users   = ref<MaintenanceUser[]>([])
const loading = ref(true)
const showAdd = ref(false)
const adding  = ref(false)
const form    = ref({ name: '', email: '', password: '', role: 'technician' })

const ROLE_COLOR: Record<string, string> = { admin: '#f59e0b', technician: '#6366f1' }

async function fetchUsers() {
  try {
    users.value = await maintenanceUserService.list()
  } catch (e: any) {
    toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function addUser() {
  if (!form.value.name || !form.value.email || !form.value.password) {
    toast('All fields required', 'error'); return
  }
  adding.value = true
  try {
    const u = await maintenanceUserService.create(form.value)
    users.value.unshift(u)
    toast(`User "${u.name}" created`)
    showAdd.value = false
    form.value = { name: '', email: '', password: '', role: 'technician' }
  } catch (e: any) {
    toast(e.message, 'error')
  } finally {
    adding.value = false
  }
}

async function toggleStatus(u: MaintenanceUser) {
  const next = u.status === 'active' ? 'inactive' : 'active'
  try {
    const updated = await maintenanceUserService.setStatus(u.id, next)
    const idx = users.value.findIndex(x => x.id === u.id)
    if (idx !== -1) users.value[idx] = updated
    toast('Status updated')
  } catch (e: any) {
    toast(e.message, 'error')
  }
}

async function deleteUser(u: MaintenanceUser) {
  if (u.id === auth.currentUser?.id) { toast('Cannot delete yourself', 'error'); return }
  if (!confirm(`Delete user "${u.name}"? This cannot be undone.`)) return
  try {
    await maintenanceUserService.delete(u.id)
    users.value = users.value.filter(x => x.id !== u.id)
    toast('User deleted', 'warning')
  } catch (e: any) {
    toast(e.message, 'error')
  }
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

onMounted(fetchUsers)
</script>

<template>
  <div class="m-users">

    <!-- Header -->
    <div class="m-page-header">
      <div class="m-page-header-text">
        <h1>Maintenance Users</h1>
        <p>{{ users.filter(u => u.status === 'active').length }} active user{{ users.filter(u => u.status === 'active').length !== 1 ? 's' : '' }}</p>
      </div>
      <button class="m-btn m-btn-primary" @click="showAdd = true">
        <i class="fa-solid fa-user-plus"></i> Add User
      </button>
    </div>

    <!-- Table -->
    <div class="m-card">
      <div v-if="loading" class="m-loading">
        <i class="fa-solid fa-spinner fa-spin"></i> Loading users…
      </div>
      <div v-else-if="users.length === 0" class="m-empty">
        <i class="fa-solid fa-users" style="font-size:2rem;display:block;margin-bottom:0.75rem;color:#d1d5db;"></i>
        No users found.
      </div>
      <div v-else class="m-table-wrap">
        <table class="m-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td style="font-weight:600;color:#111827">
                {{ u.name }}
                <span v-if="u.id === auth.currentUser?.id" style="font-size:0.6875rem;color:#9ca3af;font-weight:400;margin-left:0.375rem">(you)</span>
              </td>
              <td style="color:#6b7280;font-size:0.875rem">{{ u.email }}</td>
              <td>
                <span class="m-badge" :style="{ background: ROLE_COLOR[u.role] + '22', color: ROLE_COLOR[u.role] }">
                  <i :class="u.role === 'admin' ? 'fa-solid fa-shield-halved' : 'fa-solid fa-screwdriver-wrench'" style="margin-right:0.375rem"></i>
                  {{ u.role }}
                </span>
              </td>
              <td>
                <span
                  class="m-badge"
                  :style="{ background: u.status === 'active' ? '#f0fdf4' : '#f9fafb', color: u.status === 'active' ? '#059669' : '#9ca3af' }"
                >
                  <i :class="u.status === 'active' ? 'fa-solid fa-circle-dot' : 'fa-solid fa-circle'" style="margin-right:0.375rem"></i>
                  {{ u.status }}
                </span>
              </td>
              <td style="color:#9ca3af;font-size:0.8125rem;white-space:nowrap">{{ fmtDate(u.createdAt) }}</td>
              <td>
                <div class="m-actions">
                  <button
                    :class="['m-btn-icon', u.status === 'active' ? 'deactivate' : 'activate']"
                    :title="u.status === 'active' ? 'Deactivate user' : 'Activate user'"
                    @click="toggleStatus(u)"
                  >
                    <i :class="u.status === 'active' ? 'fa-solid fa-toggle-on' : 'fa-solid fa-toggle-off'"></i>
                  </button>
                  <button
                    v-if="u.id !== auth.currentUser?.id"
                    class="m-btn-icon danger"
                    title="Delete user"
                    @click="deleteUser(u)"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add user modal -->
    <div v-if="showAdd" class="m-modal-overlay" @click.self="showAdd = false">
      <div class="m-modal">
        <div class="m-modal-header">
          <h3><i class="fa-solid fa-user-plus" style="color:#f59e0b;margin-right:0.5rem"></i>Add Maintenance User</h3>
          <button class="m-modal-close" @click="showAdd = false"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="m-modal-body">
          <div class="m-form-group">
            <label>Full Name *</label>
            <input v-model="form.name" class="m-input" placeholder="John Smith"/>
          </div>
          <div class="m-form-group">
            <label>Email Address *</label>
            <input v-model="form.email" type="email" class="m-input" placeholder="john@haval.com"/>
          </div>
          <div class="m-form-group">
            <label>Password *</label>
            <input v-model="form.password" type="password" class="m-input" placeholder="••••••••"/>
          </div>
          <div class="m-form-group">
            <label>Role</label>
            <select v-model="form.role" class="m-select">
              <option value="technician">Technician</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        <div class="m-modal-footer">
          <button class="m-btn m-btn-secondary" @click="showAdd = false">Cancel</button>
          <button class="m-btn m-btn-primary" :disabled="adding" @click="addUser">
            <i v-if="adding" class="fa-solid fa-spinner fa-spin"></i>
            <i v-else class="fa-solid fa-user-plus"></i>
            {{ adding ? 'Creating…' : 'Create User' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped src="@/styles/pages/maintenance-users.css"></style>
