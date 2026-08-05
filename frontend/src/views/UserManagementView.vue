<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Component } from 'vue'
import { useLinesStore } from '@/stores/lines'
import { useUsersStore } from '@/stores/users'
import { useToast } from '@/composables/useToast'
import AppCard      from '@/components/ui/AppCard.vue'
import AppBadge     from '@/components/ui/AppBadge.vue'
import AppButton    from '@/components/ui/AppButton.vue'
import AppModal     from '@/components/ui/AppModal.vue'
import AppInput     from '@/components/ui/AppInput.vue'
import AppSelect    from '@/components/ui/AppSelect.vue'
import FormField    from '@/components/ui/FormField.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import UserAvatar   from '@/components/ui/UserAvatar.vue'
import PageHeader   from '@/components/ui/PageHeader.vue'
import { Plus, UserCheck, Scissors, Wrench, Settings, Building2, Flag, Construction } from 'lucide-vue-next'
import type { User } from '@/stores/auth'

const usersStore = useUsersStore()
const linesStore = useLinesStore()
const { toast }  = useToast()

const showAdd    = ref(false)
const showAssign = ref(false)
const delTgt     = ref<User | null>(null)
const form       = ref({ name: '', email: '', role: 'line_manager' })

const draftAssign = ref<Record<string, string>>({})
function openAssign() {
  draftAssign.value = Object.fromEntries(
    Object.entries(usersStore.lineManagers).map(([lid, uid]) => [lid, uid || UNASSIGNED]),
  )
  showAssign.value = true
}
async function saveAssign() {
  try {
    await Promise.all(
      Object.entries(draftAssign.value).map(([lid, uid]) =>
        usersStore.setLineManager(lid, uid === UNASSIGNED ? null : uid),
      ),
    )
    toast('Line manager assignments saved!')
    showAssign.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function addUser() {
  if (!form.value.name || !form.value.email) { toast('Name and email required', 'error'); return }
  try {
    await usersStore.addUser(form.value.name, form.value.email, form.value.role as User['role'])
    toast(`User "${form.value.name}" created!`)
    form.value = { name: '', email: '', role: 'line_manager' }; showAdd.value = false
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function toggle(id: string) {
  try { await usersStore.toggleUserStatus(id); toast('Status updated', 'info') }
  catch (e: unknown) { toast((e as Error).message, 'error') }
}

async function deleteUser(id: string) {
  try { await usersStore.deleteUser(id); toast('User deleted', 'warning') }
  catch (e: unknown) { toast((e as Error).message, 'error') }
}

const UNASSIGNED = '__none__'

const lineManagerOptions = computed(() => [
  { value: UNASSIGNED, label: '— Unassigned —' },
  ...usersStore.lineManagerUsers.map(u => ({ value: u.id, label: u.name })),
])
const roleOptions = [
  { value: 'process_manager', label: 'Process Manager' },
  { value: 'line_manager',    label: 'Line Manager'    },
]

const roleColor: Record<string, string> = { process_manager: '#6366F1', line_manager: '#8B5CF6' }
const roleLabel: Record<string, string> = { process_manager: 'Process Mgr', line_manager: 'Line Mgr' }

const LINE_ICONS: Record<string, Component> = {
  scissors: Scissors, wrench: Wrench, settings: Settings, building2: Building2,
  flag: Flag, factory: Construction,
}
</script>

<template>
  <div class="p-8">
    <div class="flex items-start justify-between mb-7">
      <PageHeader title="User Management"
        :subtitle="`${usersStore.users.filter(u=>u.status==='active').length} active users`"/>
      <div class="flex gap-2">
        <AppButton variant="secondary" @click="openAssign"><UserCheck :size="15"/> Assign Line Managers</AppButton>
        <AppButton @click="showAdd = true"><Plus :size="15"/> Add User</AppButton>
      </div>
    </div>

    <!-- Role info -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <AppCard v-for="r in [
        { role:'Process Manager', color:'#6366F1', desc:'Full access: uploads, user management, all lines, migration, settings, and audit logs.' },
        { role:'Line Manager',    color:'#8B5CF6', desc:'View-only for assigned line. Can see latest control plans and change comparisons. No upload rights.' }
      ]" :key="r.role" class="!border-l-2" :style="{ borderLeftColor: r.color }">
        <div class="text-sm font-bold mb-1" :style="{ color: r.color }">{{ r.role }}</div>
        <p class="text-xs text-surface-200 leading-relaxed m-0">{{ r.desc }}</p>
      </AppCard>
    </div>

    <!-- Line manager assignments -->
    <AppCard class="mb-6">
      <h3 class="text-sm font-bold text-slate-100 mb-4">Line Manager Assignments</h3>
      <div class="grid grid-cols-5 gap-3">
        <div v-for="line in linesStore.lines" :key="line.id"
             class="bg-surface-950 rounded-xl p-4 border transition-colors"
             :style="{ borderColor: usersStore.users.find(u=>u.id===usersStore.lineManagers[line.id]) ? line.color+'44' : '#1E2D45' }">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center mb-2" :style="{ background: line.color + '22' }">
            <component :is="LINE_ICONS[line.icon] ?? Construction" :size="16" :style="{ color: line.color }" />
          </div>
          <div class="text-xs font-bold mb-2" :style="{ color: line.color }">{{ line.name }}</div>
          <template v-if="usersStore.users.find(u=>u.id===usersStore.lineManagers[line.id])">
            <div class="flex items-center gap-1.5">
              <UserAvatar :initials="usersStore.users.find(u=>u.id===usersStore.lineManagers[line.id])?.avatar" size="sm"/>
              <span class="text-xs font-semibold text-slate-300 truncate">{{ usersStore.users.find(u=>u.id===usersStore.lineManagers[line.id])?.name }}</span>
            </div>
          </template>
          <span v-else class="text-xs text-surface-400">Unassigned</span>
        </div>
      </div>
    </AppCard>

    <!-- Users table -->
    <AppCard :no-pad="true">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-surface-800 border-b border-surface-600">
              <th v-for="h in ['User','Email','Role','Status','Joined','Actions']" :key="h"
                  class="px-4 py-3 text-left text-[10px] font-bold text-surface-300 uppercase tracking-widest">{{ h }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(u, i) in usersStore.users" :key="u.id"
                :class="['border-b border-surface-700/50', i%2===0?'':'bg-surface-950/40']">
              <td class="px-4 py-3">
                <div class="flex items-center gap-2.5">
                  <UserAvatar :initials="u.avatar"/>
                  <span class="font-semibold text-slate-300">{{ u.name }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-xs text-surface-200">{{ u.email }}</td>
              <td class="px-4 py-3"><AppBadge :color="roleColor[u.role]">{{ roleLabel[u.role] }}</AppBadge></td>
              <td class="px-4 py-3"><AppBadge :color="u.status==='active'?'#10B981':'#475569'">{{ u.status }}</AppBadge></td>
              <td class="px-4 py-3 text-xs text-surface-300">{{ u.createdAt }}</td>
              <td class="px-4 py-3">
                <div class="flex gap-2">
                  <AppButton size="sm" variant="secondary" @click="toggle(u.id)">
                    {{ u.status === 'active' ? 'Deactivate' : 'Activate' }}
                  </AppButton>
                  <AppButton size="sm" variant="danger" @click="delTgt = u">Delete</AppButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AppCard>

    <!-- Add User Modal -->
    <AppModal :open="showAdd" title="Add New User" @close="showAdd=false">
      <div class="space-y-4 mb-5">
        <FormField label="Full Name"><AppInput v-model="form.name" placeholder="Jane Smith"/></FormField>
        <FormField label="Email"><AppInput v-model="form.email" type="email" placeholder="jane@factory.com"/></FormField>
        <FormField label="Role"><AppSelect v-model="form.role" :options="roleOptions"/></FormField>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAdd=false">Cancel</AppButton>
        <AppButton @click="addUser">Create User</AppButton>
      </div>
    </AppModal>

    <!-- Assign Line Managers Modal -->
    <AppModal :open="showAssign" title="Assign Line Managers" :wide="true" @close="showAssign=false">
      <p class="text-sm text-surface-200 mb-5 leading-relaxed">
        Assign one line manager per assembly line.
      </p>
      <div class="space-y-3 mb-5">
        <div v-for="line in linesStore.lines" :key="line.id" class="flex items-center gap-4">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" :style="{ background: line.color + '22' }">
            <component :is="LINE_ICONS[line.icon] ?? Construction" :size="16" :style="{ color: line.color }" />
          </div>
          <div class="flex-1">
            <div class="text-xs font-bold text-surface-200 mb-1 uppercase tracking-wider">{{ line.name }}</div>
            <AppSelect v-model="draftAssign[line.id]" :options="lineManagerOptions"/>
          </div>
        </div>
      </div>
      <div class="flex gap-3 justify-end">
        <AppButton variant="secondary" @click="showAssign=false">Cancel</AppButton>
        <AppButton @click="saveAssign">Save Assignments</AppButton>
      </div>
    </AppModal>

    <ConfirmDialog :open="!!delTgt" title="Delete User" danger label="Delete User"
      :message="`Permanently delete &quot;${delTgt?.name}&quot;?`"
      @close="delTgt=null"
      @confirm="deleteUser(delTgt!.id); delTgt=null"/>
  </div>
</template>
