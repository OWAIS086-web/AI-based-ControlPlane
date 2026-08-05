import { ROLES } from './roles.enum'

export const ROUTES = {
  dashboardView: {
    path: 'dashboard',
    name: 'dashboard',
    roles_required: [ROLES.lineManager, ROLES.processManager],
  },
  assemblyLineView: {
    path: 'lines/:lineId',
    name: 'assembly-line',
    roles_required: [ROLES.lineManager, ROLES.processManager],
  },
  processDetailView: {
    path: 'lines/:lineId/processes/:processId',
    name: 'process-detail',
    roles_required: [ROLES.lineManager, ROLES.processManager],
  },
  processManagementView: {
    path: 'control-plans',
    name: 'control-plans',
    roles_required: [ROLES.processManager],
  },
  carModelsView: {
    path: 'car-models',
    name: 'car-models',
    roles_required: [ROLES.processManager],
  },
  migrationView: {
    path: 'migration',
    name: 'migration',
    roles_required: [ROLES.processManager],
  },
  auditLedgerView: {
    path: 'audit',
    name: 'audit',
    roles_required: [ROLES.processManager],
  },
  lineManagementView: {
    path: 'line-management',
    name: 'line-management',
    roles_required: [ROLES.processManager],
  },
  workerAssignmentView: {
    path: 'worker-assignment',
    name: 'worker-assignment',
    roles_required: [ROLES.processManager],
  },
  workerManagementView: {
    path: 'workers',
    name: 'workers',
    roles_required: [ROLES.processManager],
  },
  toolAllocationView: {
    path: 'tool-allocation',
    name: 'tool-allocation',
    roles_required: [ROLES.processManager],
  },
  toolManagementView: {
    path: 'tools',
    name: 'tools',
    roles_required: [ROLES.processManager],
  },
  toolRequestsView: {
    path: 'tool-requests',
    name: 'tool-requests',
    roles_required: [ROLES.processManager, ROLES.lineManager],
  },
  userManagementView: {
    path: 'users',
    name: 'users',
    roles_required: [ROLES.processManager],
  },
  settingsView: {
    path: 'settings',
    name: 'settings',
    roles_required: [ROLES.processManager, ROLES.lineManager],
  },
  loginView: {
    path: 'login',
    name: 'login',
    roles_required: [],
  },
  supportView: {
    path: 'support',
    name: 'support',
    roles_required: [],
  },
  notFound: {
    path: '/not-found',
    name: 'not-found',
    roles_required: [],
  },

  // ── Maintenance portal ────────────────────────────────────────────────────
  maintenanceLogin: {
    path: '/maintenance/login',
    name: 'maintenance-login',
    roles_required: [],
  },
  maintenanceDashboard: {
    path: '/maintenance/dashboard',
    name: 'maintenance-dashboard',
    roles_required: [],
  },
  maintenanceFaults: {
    path: '/maintenance/faults',
    name: 'maintenance-faults',
    roles_required: [],
  },
  maintenanceFaultsNew: {
    path: '/maintenance/faults/new',
    name: 'maintenance-faults-new',
    roles_required: [],
  },
  maintenanceFaultDetail: {
    path: '/maintenance/faults/:id',
    name: 'maintenance-fault-detail',
    roles_required: [],
  },
  maintenanceAnalytics: {
    path: '/maintenance/analytics',
    name: 'maintenance-analytics',
    roles_required: [],
  },
  maintenanceUsers: {
    path: '/maintenance/users',
    name: 'maintenance-users',
    roles_required: [],
  },
} as const