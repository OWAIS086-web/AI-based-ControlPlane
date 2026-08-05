<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useToast } from '@/composables/useToast'
import { usersService } from '@/services/users.service'
import { authService } from '@/services/auth.service'
import AppCard    from '@/components/ui/AppCard.vue'
import AppButton  from '@/components/ui/AppButton.vue'
import AppInput   from '@/components/ui/AppInput.vue'
import FormField  from '@/components/ui/FormField.vue'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const auth        = useAuthStore()
const configStore = useConfigStore()
const { toast }   = useToast()

onMounted(() => configStore.fetchConfig())

// ── Tabs ─────────────────────────────────────────────────────────────────────
type Tab = 'profile' | 'notifications' | 'security' | 'system'
const activeTab = ref<Tab>('profile')
const tabs = [
  { id: 'profile'       as Tab, label: 'Profile',       pmOnly: false },
  { id: 'notifications' as Tab, label: 'Notifications', pmOnly: false },
  { id: 'security'      as Tab, label: 'Security',      pmOnly: false },
  { id: 'system'        as Tab, label: 'System',        pmOnly: true  },
]
const visibleTabs = tabs.filter(t => !t.pmOnly || auth.isPM)

// ── Profile ───────────────────────────────────────────────────────────────────
const displayName = ref(auth.currentUser?.name  ?? '')
const email       = ref(auth.currentUser?.email ?? '')

async function saveProfile() {
  try {
    const updated = await usersService.update(auth.currentUser!.id, {
      name: displayName.value,
      email: email.value,
    })
    auth.currentUser = { ...auth.currentUser!, ...updated }
    toast('Profile updated!')
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ── Notifications ─────────────────────────────────────────────────────────────
const notifs = ref({ newUploads: true, migrations: false, userChanges: true, systemAlerts: true })

async function saveNotifications() {
  try {
    await usersService.updateSettings(auth.currentUser!.id, {
      notifications: notifs.value,
    })
    toast('Notification preferences saved!')
  } catch (e: unknown) { toast((e as Error).message, 'error') }
}

// ── Security ──────────────────────────────────────────────────────────────────
const currentPassword  = ref('')
const newPassword      = ref('')
const confirmPassword  = ref('')
const passwordSaving   = ref(false)

async function changePassword() {
  if (newPassword.value !== confirmPassword.value) {
    toast('New passwords do not match', 'error')
    return
  }
  if (newPassword.value.length < 8) {
    toast('Password must be at least 8 characters', 'error')
    return
  }
  passwordSaving.value = true
  try {
    await authService.changePassword(currentPassword.value, newPassword.value)
    toast('Password changed successfully!')
    currentPassword.value = ''
    newPassword.value     = ''
    confirmPassword.value = ''
  } catch (e: unknown) { toast((e as Error).message, 'error') }
  finally { passwordSaving.value = false }
}
</script>

<template>
  <div class="p-8 max-w-2xl">
    <PageHeader title="Settings" subtitle="Manage your account preferences"/>

    <!-- Tab bar -->
    <div class="flex gap-1 mb-6 border-b border-surface-700">
      <button
        v-for="tab in visibleTabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                 activeTab === tab.id
                   ? 'text-brand-400 border-brand-500'
                   : 'text-surface-300 border-transparent hover:text-slate-200']">
        {{ tab.label }}
      </button>
    </div>

    <!-- Profile tab -->
    <AppCard v-if="activeTab === 'profile'">
      <div class="flex items-center gap-4 mb-6">
        <UserAvatar :initials="auth.currentUser?.avatar" size="lg"/>
        <div>
          <div class="text-base font-bold text-slate-200">{{ auth.currentUser?.name }}</div>
          <div class="text-xs text-surface-200 capitalize">{{ auth.currentUser?.role?.replace('_',' ') }}</div>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 mb-4">
        <FormField label="Display Name"><AppInput v-model="displayName"/></FormField>
        <FormField label="Email"><AppInput v-model="email" type="email"/></FormField>
      </div>
      <div class="flex justify-end">
        <AppButton @click="saveProfile">Save Profile</AppButton>
      </div>
    </AppCard>

    <!-- Notifications tab -->
    <AppCard v-if="activeTab === 'notifications'">
      <div
        v-for="[key, label] in [['newUploads','New Uploads'],['migrations','Migrations'],['userChanges','User Changes'],['systemAlerts','System Alerts']]"
        :key="key"
        class="flex items-center justify-between py-3 border-b border-surface-700 last:border-0">
        <div>
          <div class="text-sm font-medium text-slate-300">{{ label }}</div>
          <div class="text-xs text-surface-300">Email notification when this event occurs</div>
        </div>
        <button @click="notifs[key] = !notifs[key]"
          :class="['relative w-11 h-6 rounded-full border-none cursor-pointer transition-colors duration-200', notifs[key] ? 'bg-brand-500' : 'bg-surface-600']">
          <span :class="['absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all duration-200 shadow', notifs[key] ? 'left-[22px]' : 'left-0.5']"/>
        </button>
      </div>
      <div class="flex justify-end mt-4">
        <AppButton @click="saveNotifications">Save Preferences</AppButton>
      </div>
    </AppCard>

    <!-- System tab (PM only) -->
    <AppCard v-if="activeTab === 'system'">
      <h3 class="text-sm font-bold text-slate-100 mb-1">Process Card Display</h3>
      <p class="text-xs text-surface-300 mb-5">Choose what label is shown on process cards across all assembly line views.</p>
      <div class="space-y-3">
        <label v-for="opt in [{ value: 'name', label: 'Process Name', desc: 'Show the process name assigned when the process was created.' }, { value: 'filename', label: 'File Name', desc: 'Show the original filename of the most recently uploaded control plan.' }]"
          :key="opt.value"
          :class="['flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all',
                   configStore.cardDisplayMode === opt.value
                     ? 'border-brand-500/60 bg-brand-500/8'
                     : 'border-surface-600 hover:border-surface-500']">
          <input type="radio" name="cardDisplayMode" :value="opt.value"
            :checked="configStore.cardDisplayMode === opt.value"
            @change="configStore.setCardDisplayMode(opt.value as 'name' | 'filename').then(() => toast('Display setting saved!'))"
            class="mt-0.5 accent-brand-500 cursor-pointer"/>
          <div>
            <div class="text-sm font-semibold text-slate-200">{{ opt.label }}</div>
            <div class="text-xs text-surface-300 mt-0.5">{{ opt.desc }}</div>
          </div>
        </label>
      </div>
    </AppCard>

    <!-- Security tab -->
    <AppCard v-if="activeTab === 'security'">
      <h3 class="text-sm font-bold text-slate-100 mb-5">Change Password</h3>
      <div class="space-y-4 mb-5">
        <FormField label="Current Password">
          <AppInput v-model="currentPassword" type="password" placeholder="Enter current password"/>
        </FormField>
        <FormField label="New Password">
          <AppInput v-model="newPassword" type="password" placeholder="At least 8 characters"/>
        </FormField>
        <FormField label="Confirm New Password">
          <AppInput v-model="confirmPassword" type="password" placeholder="Repeat new password"/>
        </FormField>
      </div>
      <div class="flex justify-end">
        <AppButton @click="changePassword" :disabled="passwordSaving">
          {{ passwordSaving ? 'Saving…' : 'Update Password' }}
        </AppButton>
      </div>
    </AppCard>
  </div>
</template>
