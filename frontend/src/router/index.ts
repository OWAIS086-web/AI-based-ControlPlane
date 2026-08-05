import { createRouter, createWebHistory } from 'vue-router'
import { ROUTES } from '@/constants/routeConstant'
import { ROLES } from '@/constants/roles.enum'

const LoginLayout       = () => import('@/layouts/LoginLayout.vue')
const DefaultLayout     = () => import('@/layouts/DefaultLayout.vue')
const MaintenanceLayout = () => import('@/layouts/MaintenanceLayout.vue')

const routes = [
  // 1. ROOT REDIRECT
  {
    path: '/',
    name: 'root',
    redirect: () => {
      const isAuthenticated = !!localStorage.getItem('cp_access_token')
      return isAuthenticated
        ? `/${ROUTES.dashboardView.path}`
        : `/${ROUTES.loginView.path}`
    },
  },

  // 2. GUEST ROUTES
  {
    path: '/',
    component: LoginLayout,
    children: [
      {
        path: ROUTES.loginView.path,
        name: ROUTES.loginView.name,
        component: () => import('@/views/LoginView.vue'),
        meta: { requiresGuest: true },
      },
    ],
  },

  // 3. AUTHENTICATED ROUTES
  {
    path: '/',
    component: DefaultLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: ROUTES.dashboardView.path,
        name: ROUTES.dashboardView.name,
        component: () => import('@/views/DashboardView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.dashboardView.roles_required },
      },
      {
        path: ROUTES.assemblyLineView.path,
        name: ROUTES.assemblyLineView.name,
        component: () => import('@/views/AssemblyLineView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.assemblyLineView.roles_required },
      },
      {
        path: ROUTES.processDetailView.path,
        name: ROUTES.processDetailView.name,
        component: () => import('@/views/ProcessDetailView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.processDetailView.roles_required },
      },
      {
        path: ROUTES.processManagementView.path,
        name: ROUTES.processManagementView.name,
        component: () => import('@/views/ProcessManagementView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.processManagementView.roles_required },
      },
      {
        path: ROUTES.carModelsView.path,
        name: ROUTES.carModelsView.name,
        component: () => import('@/views/CarModelsView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.carModelsView.roles_required },
      },
      {
        path: ROUTES.migrationView.path,
        name: ROUTES.migrationView.name,
        component: () => import('@/views/MigrationView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.migrationView.roles_required },
      },
      {
        path: ROUTES.auditLedgerView.path,
        name: ROUTES.auditLedgerView.name,
        component: () => import('@/views/AuditLedgerView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.auditLedgerView.roles_required },
      },
      {
        path: ROUTES.lineManagementView.path,
        name: ROUTES.lineManagementView.name,
        component: () => import('@/views/LineManagementView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.lineManagementView.roles_required },
      },
      {
        path: ROUTES.workerAssignmentView.path,
        name: ROUTES.workerAssignmentView.name,
        component: () => import('@/views/WorkerAssignmentView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.workerAssignmentView.roles_required },
      },
      {
        path: ROUTES.workerManagementView.path,
        name: ROUTES.workerManagementView.name,
        component: () => import('@/views/WorkerManagementView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.workerManagementView.roles_required },
      },
      {
        path: ROUTES.toolAllocationView.path,
        name: ROUTES.toolAllocationView.name,
        component: () => import('@/views/ToolAllocationView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.toolAllocationView.roles_required },
      },
      {
        path: ROUTES.toolManagementView.path,
        name: ROUTES.toolManagementView.name,
        component: () => import('@/views/ToolManagementView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.toolManagementView.roles_required },
      },
      {
        path: ROUTES.toolRequestsView.path,
        name: ROUTES.toolRequestsView.name,
        component: () => import('@/views/ToolRequestsView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.toolRequestsView.roles_required },
      },
      {
        path: ROUTES.userManagementView.path,
        name: ROUTES.userManagementView.name,
        component: () => import('@/views/UserManagementView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.userManagementView.roles_required },
      },
      {
        path: ROUTES.settingsView.path,
        name: ROUTES.settingsView.name,
        component: () => import('@/views/SettingsView.vue'),
        meta: { requiresAuth: true, roles_required: ROUTES.settingsView.roles_required },
      },
      {
        path: ROUTES.notFound.path,
        name: ROUTES.notFound.name,
        component: () => import('@/views/NotFoundView.vue'),
      },
      {
        path: ROUTES.supportView.path,
        name: ROUTES.supportView.name,
        component: () => import('@/views/SupportView.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },

  // 4. MAINTENANCE PORTAL — guest route
  {
    path: ROUTES.maintenanceLogin.path,
    component: LoginLayout,
    children: [
      {
        path: '',
        name: ROUTES.maintenanceLogin.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceLoginPage.vue'),
        meta: { maintenanceGuest: true },
      },
    ],
  },

  // 5. MAINTENANCE PORTAL — authenticated routes
  {
    path: '/maintenance',
    component: MaintenanceLayout,
    meta: { requiresMaintenance: true },
    children: [
      {
        path: 'dashboard',
        name: ROUTES.maintenanceDashboard.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceDashboardPage.vue'),
      },
      {
        path: 'faults',
        name: ROUTES.maintenanceFaults.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceFaultsPage.vue'),
      },
      {
        path: 'faults/:id',
        name: ROUTES.maintenanceFaultDetail.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceFaultDetailPage.vue'),
      },
      {
        path: 'analytics',
        name: ROUTES.maintenanceAnalytics.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceAnalyticsPage.vue'),
      },
      {
        path: 'users',
        name: ROUTES.maintenanceUsers.name,
        component: () => import('@/modules/maintenance/pages/MaintenanceUsersPage.vue'),
        meta: { requiresMaintenanceAdmin: true },
      },
      // Paint Inspection
      {
        path: 'paint-inspection',
        name: 'paint-inspection-dashboard',
        component: () => import('@/modules/paint-inspection/pages/PaintInspectionDashboardPage.vue'),
      },
      {
        path: 'paint-inspection/history',
        name: 'paint-inspection-history',
        component: () => import('@/modules/paint-inspection/pages/PaintInspectionHistoryPage.vue'),
      },
      {
        path: 'paint-inspection/new',
        name: 'paint-inspection-new',
        component: () => import('@/modules/paint-inspection/pages/PaintInspectionFormPage.vue'),
      },
      {
        path: 'paint-inspection/edit/:id',
        name: 'paint-inspection-edit',
        component: () => import('@/modules/paint-inspection/pages/PaintInspectionFormPage.vue'),
      },
      {
        path: 'paint-inspection/view/:id',
        name: 'paint-inspection-view',
        component: () => import('@/modules/paint-inspection/pages/PaintInspectionViewPage.vue'),
      },
    ],
  },

  // 6. CATCH ALL
  {
    path: '/:pathMatch(.*)*',
    redirect: ROUTES.notFound.path,
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// --- NAVIGATION GUARD ---
router.beforeEach((to, _from, next) => {
  const token    = localStorage.getItem('cp_access_token')
  const userRaw  = localStorage.getItem('cp_user')
  const userRole = userRaw ? (JSON.parse(userRaw) as { role: string }).role : null

  // ── Maintenance portal guards ─────────────────────────────────────────────
  const mToken   = localStorage.getItem('m_access_token')
  const mUserRaw = localStorage.getItem('m_user')
  const mUser    = mUserRaw ? (JSON.parse(mUserRaw) as { role: string }) : null

  if (to.matched.some(r => r.meta.maintenanceGuest)) {
    return mToken ? next({ name: ROUTES.maintenanceDashboard.name }) : next()
  }

  if (to.matched.some(r => r.meta.requiresMaintenance)) {
    if (!mToken) return next({ name: ROUTES.maintenanceLogin.name })
    if (to.matched.some(r => r.meta.requiresMaintenanceAdmin) && mUser?.role !== 'admin') {
      return next({ name: ROUTES.maintenanceDashboard.name })
    }
    return next()
  }

  // Guest-only routes (e.g. login) — redirect authenticated users away
  if (to.matched.some(r => r.meta.requiresGuest)) {
    return token ? next({ name: ROUTES.dashboardView.name }) : next()
  }

  // Auth-required routes
  if (to.matched.some(r => r.meta.requiresAuth)) {
    if (!token) {
      return next({ name: ROUTES.loginView.name })
    }

    const isLM = userRole === ROLES.lineManager

    // ── Role check ────────────────────────────────────────────────────────────
    const rolesRequired = to.meta.roles_required as string[] | undefined
    if (rolesRequired && rolesRequired.length > 0 && userRole) {
      if (!rolesRequired.includes(userRole)) {
        // LM tried to access a PM-only route
        return next({ name: ROUTES.notFound.name })
      }
    }

    // ── Line access check (LM only) ───────────────────────────────────────────
    // Prevent a LM from navigating to a line not assigned to them, or to the
    // dashboard, by validating against the assigned lines saved in localStorage.
    if (isLM) {
      const assignedRaw   = localStorage.getItem('cp_assigned_lines')
      const assignedLines = assignedRaw ? (JSON.parse(assignedRaw) as string[]) : []

      // No lines assigned at all — always land on the unassigned error screen
      if (assignedLines.length === 0) {
        if (to.name !== ROUTES.notFound.name) {
          return next({ name: ROUTES.notFound.name, state: { reason: 'unassigned' } })
        }
        return next()
      }

      // LM tried to open a specific lineId that isn't theirs
      if (to.name === ROUTES.assemblyLineView.name || to.name === ROUTES.processDetailView.name) {
        const lineId = to.params.lineId as string
        if (lineId && !assignedLines.includes(lineId)) {
          // Bounce to their first valid line instead
          return next({ name: ROUTES.assemblyLineView.name, params: { lineId: assignedLines[0] } })
        }
      }

      // LM tried to hit dashboard or any other non-line route — send to first line
      const lmAllowedNames = [
        ROUTES.assemblyLineView.name,
        ROUTES.processDetailView.name,
        ROUTES.settingsView.name,
        ROUTES.supportView.name,
        ROUTES.notFound.name,
        ROUTES.toolRequestsView.name,
      ] as string[]
      if (!lmAllowedNames.includes(to.name as string)) {
        return next({ name: ROUTES.assemblyLineView.name, params: { lineId: assignedLines[0] } })
      }
    }

    return next()
  }

  next()
})

export default router