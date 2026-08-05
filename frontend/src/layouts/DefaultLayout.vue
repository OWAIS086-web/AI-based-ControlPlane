<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ROLES } from '@/constants/roles.enum'
import { ROUTES } from '@/constants/routeConstant'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/auth.service'
import { useUsersStore } from '@/stores/users'
import { useLinesStore } from '@/stores/lines'
import AppNavbar from '@/components/AppNavbar.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import RouteProgress from '@/components/ui/RouteProgress.vue'

const router     = useRouter()
const auth       = useAuthStore()
const usersStore = useUsersStore()
const linesStore = useLinesStore()

const bootstrapping = ref(true)
const appVersion    = ref('')

/** Lines grouped by type for the sidebar, filtered to what the current user can see */
const myLinesByType = computed(() => {
  if (!auth.currentUser) return []

  if (auth.isPM) {
    const groups = [...linesStore.linesByType]
    // Append a virtual "Unassigned" group if any lines have no type
    if (linesStore.untypedLines.length > 0) {
      groups.push({
        id: '__unassigned__',
        name: 'Unassigned',
        icon: 'construction',
        color: '#64748B',
        order: 9999,
        lines: linesStore.untypedLines,
      })
    }
    return groups
  }

  // LM: only show types that have at least one line assigned to them
  return linesStore.linesByType
    .map(group => ({
      ...group,
      lines: group.lines.filter(l => usersStore.lineManagers[l.id] === auth.currentUser!.id),
    }))
    .filter(group => group.lines.length > 0)
})

onMounted(async () => {
  authService.getVersion().then(v => { appVersion.value = v }).catch(() => {})

  if (!auth.currentUser) {
    await auth.fetchMe()
  }

  if (!auth.currentUser) {
    router.replace({ name: ROUTES.loginView.name })
    bootstrapping.value = false
    return
  }

  const isLM = auth.currentUser.role === ROLES.lineManager
  const isPM = auth.currentUser.role === ROLES.processManager

  if (isPM) {
    await Promise.all([
      usersStore.fetchUsers(),
      usersStore.fetchLineManagers(),
      linesStore.fetchAll(),
    ])
  } else if (isLM) {
    await Promise.all([
      usersStore.fetchLineManagers(),
      linesStore.fetchAll(),
    ])

    const assignedLines = linesStore.lines.filter(
      l => usersStore.lineManagers[l.id] === auth.currentUser!.id,
    )
    localStorage.setItem('cp_assigned_lines', JSON.stringify(assignedLines.map(l => l.id)))

    if (assignedLines.length > 0) {
      router.replace({ name: ROUTES.assemblyLineView.name, params: { lineId: assignedLines[0].id } })
    } else {
      router.replace({ name: ROUTES.notFound.name, state: { reason: 'unassigned' } })
    }
  }

  bootstrapping.value = false
})
</script>

<template>
  <RouteProgress/>
  <div v-if="bootstrapping" class="flex min-h-screen items-center justify-center bg-surface-950"/>
  <template v-else>
    <div class="flex h-screen bg-surface-950 font-sans">
      <AppNavbar :line-types="myLinesByType" :version="appVersion"/>
      <main class="flex-1 overflow-y-auto min-w-0">
        <RouterView/>
      </main>
    </div>
    <ToastContainer/>
  </template>
</template>
