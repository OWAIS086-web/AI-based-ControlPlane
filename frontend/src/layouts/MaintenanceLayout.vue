<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMaintenanceAuthStore } from '@/stores/maintenanceAuth'
import { useToast } from '@/composables/useToast'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import RouteProgress  from '@/components/ui/RouteProgress.vue'

const router = useRouter()
const route  = useRoute()
const auth   = useMaintenanceAuthStore()
const { toast } = useToast()

const collapsed     = ref(false)
const bootstrapping = ref(true)

const navItems = [
  { name: 'maintenance-dashboard',  label: 'Dashboard', icon: 'fa-solid fa-gauge' },
  { name: 'maintenance-faults',     label: 'PI History', icon: 'fa-solid fa-spray-can-sparkles' },
  { name: 'maintenance-analytics',  label: 'Analytics', icon: 'fa-solid fa-chart-bar' },
]

const FORM_ROUTES = new Set(['paint-inspection-new', 'paint-inspection-edit'])

onMounted(() => {
  auth.restoreSession()
  if (!auth.isLoggedIn) { router.replace({ name: 'maintenance-login' }) }
  bootstrapping.value = false
})

watch(
  () => route.name,
  (name) => { if (FORM_ROUTES.has(name as string)) collapsed.value = true },
)

const isActive = (name: string) => route.name === name

async function logout() {
  await auth.logout()
  toast('Logged out successfully')
  router.push({ name: 'maintenance-login' })
}
</script>

<template>
  <RouteProgress/>
  <div v-if="bootstrapping" class="m-layout" style="align-items:center;justify-content:center;">
    <i class="fa-solid fa-spinner fa-spin" style="font-size:1.5rem;color:#f59e0b;"></i>
  </div>

  <template v-else>
    <div class="m-layout">

      <!-- Sidebar -->
      <aside :class="['m-sidebar', collapsed ? 'collapsed' : 'expanded']">

        <!-- Logo -->
        <div class="m-sidebar-header">
          <div class="m-sidebar-icon">
            <i class="fa-solid fa-wrench"></i>
          </div>
          <div v-if="!collapsed" class="m-sidebar-title">
            <strong>Maintenance</strong>
            <span>Portal</span>
          </div>
          <button class="m-collapse-btn" @click="collapsed = !collapsed" :title="collapsed ? 'Expand' : 'Collapse'">
            <i :class="collapsed ? 'fa-solid fa-chevron-right' : 'fa-solid fa-chevron-left'"></i>
          </button>
        </div>

        <!-- Nav -->
        <nav class="m-nav">
          <button
            v-for="item in navItems"
            :key="item.name"
            :class="['m-nav-item', { active: isActive(item.name) }]"
            @click="router.push({ name: item.name })"
            :title="collapsed ? item.label : undefined"
          >
            <i :class="item.icon"></i>
            <span v-if="!collapsed">{{ item.label }}</span>
          </button>

          <!-- Admin section -->
          <template v-if="auth.isAdmin">
            <div v-if="!collapsed" class="m-nav-section-label">Admin</div>
            <div v-else class="m-nav-divider"></div>
            <button
              :class="['m-nav-item', { active: isActive('maintenance-users') }]"
              @click="router.push({ name: 'maintenance-users' })"
              :title="collapsed ? 'Users' : undefined"
            >
              <i class="fa-solid fa-users"></i>
              <span v-if="!collapsed">Users</span>
            </button>
          </template>
        </nav>

        <!-- User chip -->
        <div class="m-user-chip">
          <div class="m-user-avatar">{{ auth.currentUser?.name?.[0]?.toUpperCase() }}</div>
          <div v-if="!collapsed" class="m-user-info">
            <strong>{{ auth.currentUser?.name }}</strong>
            <span>{{ auth.currentUser?.role }}</span>
          </div>
          <button v-if="!collapsed" class="m-logout-btn" title="Logout" @click="logout">
            <i class="fa-solid fa-right-from-bracket"></i>
          </button>
        </div>
      </aside>

      <!-- Main content -->
      <main class="m-main">
        <RouterView/>
      </main>
    </div>

    <!-- Persistent New Inspection FAB -->
    <button
      v-if="!FORM_ROUTES.has(route.name as string)"
      class="m-fab-new-inspection"
      title="New Paint Inspection"
      @click="router.push({ name: 'paint-inspection-new' })"
    >
      <i class="fa-solid fa-plus"></i>
      <span>New Inspection</span>
    </button>

    <ToastContainer/>
  </template>
</template>

<style scoped src="@/styles/pages/maintenance-layout.css"></style>
