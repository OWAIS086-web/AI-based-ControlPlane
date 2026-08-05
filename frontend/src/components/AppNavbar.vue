<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useLinesStore } from '@/stores/lines'
import type { LineTypeWithLines } from '@/stores/lines'
import UserAvatar from './ui/UserAvatar.vue'
import { ROUTES } from '@/constants/routeConstant'
import type { Component } from 'vue'
import {
  LayoutDashboard, Scissors, Wrench, Settings, Building2, Flag,
  ClipboardList, RefreshCw, Car, BarChart3, Users, LogOut,
  ChevronLeft, ChevronRight, ChevronDown, LifeBuoy, Sun, Moon, Plus,
  Zap, Box, Layers, Package, Cpu, Activity, Gauge, Cog,
  Construction, Factory, Hammer, LayoutGrid, SlidersHorizontal, UserCog, HardHat, AlertTriangle,
} from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

defineProps<{ lineTypes: LineTypeWithLines[]; version?: string }>()

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const linesStore = useLinesStore()
const { toast } = useToast()
const collapsed = ref(false)
const { isDark, toggle: toggleTheme } = useTheme()

const COLLAPSED_TYPES_KEY = 'cp_collapsed_types'

function loadCollapsedTypes(): Set<string> {
  try {
    const raw = localStorage.getItem(COLLAPSED_TYPES_KEY)
    return new Set(raw ? JSON.parse(raw) : [])
  } catch { return new Set() }
}

const collapsedTypes = ref<Set<string>>(loadCollapsedTypes())

function toggleType(id: string) {
  const next = new Set(collapsedTypes.value)
  next.has(id) ? next.delete(id) : next.add(id)
  collapsedTypes.value = next
  localStorage.setItem(COLLAPSED_TYPES_KEY, JSON.stringify([...next]))
}

// ─── Icon map (lowercase icon names → lucide components) ─────────────────────
const ICON_MAP: Record<string, Component> = {
  scissors: Scissors,
  wrench: Wrench,
  settings: Settings,
  building2: Building2,
  flag: Flag,
  car: Car,
  zap: Zap,
  box: Box,
  layers: Layers,
  package: Package,
  cpu: Cpu,
  activity: Activity,
  gauge: Gauge,
  cog: Cog,
  factory: Factory,
  hammer: Hammer,
  grid: LayoutGrid,
  construction: Construction,
}

function iconFor(name: string): Component {
  return ICON_MAP[name?.toLowerCase()] ?? Construction
}

const navCategories = computed(() => {
  if (!auth.isPM) return []
  return [
    {
      label: 'Tools',
      items: [
        { routeName: ROUTES.toolRequestsView.name,  label: 'Tool Requests',   Icon: AlertTriangle },
        { routeName: ROUTES.toolAllocationView.name, label: 'Tool Allocation', Icon: Wrench        },
        { routeName: ROUTES.toolManagementView.name, label: 'Tool Management', Icon: Package       },
      ],
    },
    {
      label: 'Workers',
      items: [
        { routeName: ROUTES.workerAssignmentView.name, label: 'Assignment', Icon: HardHat  },
        { routeName: ROUTES.workerManagementView.name, label: 'Management', Icon: UserCog  },
      ],
    },
    {
      label: 'Control Plans',
      items: [
        { routeName: ROUTES.lineManagementView.name,    label: 'Lines',     Icon: SlidersHorizontal },
        { routeName: ROUTES.processManagementView.name, label: 'Processes', Icon: ClipboardList     },
        { routeName: ROUTES.migrationView.name,         label: 'Migration', Icon: RefreshCw         },
      ],
    },
    {
      label: 'System',
      items: [
        { routeName: ROUTES.carModelsView.name,      label: 'Car Models',      Icon: Car      },
        { routeName: ROUTES.auditLedgerView.name,    label: 'Audit Ledger',    Icon: BarChart3 },
        { routeName: ROUTES.userManagementView.name, label: 'User Management', Icon: Users    },
        { routeName: ROUTES.settingsView.name,       label: 'Settings',        Icon: Settings },
      ],
    },
  ]
})

function navTo(name: string, params?: Record<string, string>) {
  router.push({ name, params })
}

async function logout() {
  await auth.logout()
  toast('Logged out')
  router.push({ name: ROUTES.loginView.name })
}

const isActive     = (name: string)   => route.name === name
const isActiveLine = (lineId: string) => route.params.lineId === lineId

// ─── Quick-add line modal ─────────────────────────────────────────────────────
const addLineOpen   = ref(false)
const addLineTypeId = ref<string | null>(null)
const addLineForm   = ref({ name: '', icon: 'factory', color: '#6366F1' })
const addLineLoading = ref(false)

const AVAILABLE_ICONS = [
  'scissors', 'wrench', 'settings', 'building2', 'flag',
  'car', 'zap', 'box', 'layers', 'package', 'cpu',
  'activity', 'gauge', 'cog', 'factory', 'hammer',
]

function openAddLine(typeId: string) {
  addLineTypeId.value = typeId
  addLineForm.value   = { name: '', icon: 'factory', color: '#6366F1' }
  addLineOpen.value   = true
}

async function submitAddLine() {
  if (!addLineForm.value.name.trim()) { toast('Name is required', 'error'); return }
  addLineLoading.value = true
  try {
    await linesStore.createLine({
      name:       addLineForm.value.name.trim(),
      icon:       addLineForm.value.icon,
      color:      addLineForm.value.color,
      lineTypeId: addLineTypeId.value,
    })
    toast(`Line "${addLineForm.value.name}" added!`)
    addLineOpen.value = false
  } catch (e: unknown) {
    toast((e as Error).message, 'error')
  } finally {
    addLineLoading.value = false
  }
}
</script>

<template>
  <aside :class="['flex flex-col h-full bg-surface-950 border-r border-surface-700 transition-all duration-300 flex-shrink-0', collapsed ? 'w-16' : 'w-60']">
    <!-- Logo -->
    <div class="flex items-center gap-2.5 px-4 py-4 border-b border-surface-700">
      <img src="/favicon.svg" @click="collapsed = false" class="w-8 h-8 rounded-lg flex-shrink-0 cursor-pointer" alt="logo"/>
      <div v-if="!collapsed" class="flex flex-col min-w-0">
        <span class="text-sm font-black text-slate-100 whitespace-nowrap">VRD-ControlPlan</span>
        <span v-if="version" class="text-[10px] text-surface-400 font-mono">{{ version }}</span>
      </div>
      <button @click="collapsed = !collapsed" class="ml-auto text-surface-300 hover:text-slate-100 transition-colors flex-shrink-0">
        <ChevronLeft v-if="!collapsed" :size="16"/>
        <ChevronRight v-else :size="16"/>
      </button>
    </div>

    <!-- Nav -->
    <nav class="flex-1 px-2 py-3 overflow-y-auto overflow-x-hidden space-y-0.5">
      <!-- Dashboard -->
      <button v-if="auth.isPM" @click="navTo(ROUTES.dashboardView.name)"
        :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                 isActive(ROUTES.dashboardView.name) ? 'bg-brand-500/15 text-brand-400 border-brand-500' : 'text-surface-200 hover:bg-surface-700 border-transparent']">
        <LayoutDashboard :size="16" class="flex-shrink-0"/>
        <span v-if="!collapsed" class="truncate">Dashboard</span>
      </button>

      <!-- Line type groups -->
      <template v-for="group in lineTypes" :key="group.id">
        <!-- Type header -->
        <div v-if="!collapsed" class="flex items-center justify-between px-2.5 pt-4 pb-1">
          <button @click="toggleType(group.id)"
            class="flex items-center gap-1 text-[10px] font-bold text-surface-500 uppercase tracking-widest hover:text-surface-300 transition-colors">
            <ChevronDown :size="11"
              :class="['transition-transform duration-200', collapsedTypes.has(group.id) ? '-rotate-90' : '']"/>
            {{ group.name }}
          </button>
          <button v-if="auth.isPM" @click="openAddLine(group.id)"
            class="text-surface-500 hover:text-brand-400 transition-colors"
            :title="`Add ${group.name} Line`">
            <Plus :size="12"/>
          </button>
        </div>
        <div v-else class="border-t border-surface-700 my-2"/>

        <!-- Lines within this type -->
        <template v-if="!collapsedTypes.has(group.id)">
        <button v-for="line in group.lines" :key="line.id"
          @click="navTo(ROUTES.assemblyLineView.name, { lineId: line.id })"
          :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                   isActiveLine(line.id) ? 'border-l-2 text-white' : 'text-surface-200 hover:bg-surface-700 border-transparent']"
          :style="isActiveLine(line.id) ? { background: line.color+'22', borderColor: line.color, color: line.color } : {}">
          <component :is="iconFor(line.icon)" :size="16" class="flex-shrink-0"/>
          <span v-if="!collapsed" class="truncate">{{ line.name }}</span>
        </button>
        </template>
      </template>

      <!-- PM: categorised nav -->
      <template v-if="auth.isPM">
        <template v-for="cat in navCategories" :key="cat.label">
          <div v-if="!collapsed" class="px-2.5 pt-4 pb-1 text-[10px] font-bold text-surface-500 uppercase tracking-widest">{{ cat.label }}</div>
          <div v-else class="border-t border-surface-700 my-2"/>
          <button v-for="item in cat.items" :key="item.routeName" @click="navTo(item.routeName)"
            :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                     isActive(item.routeName) ? 'bg-brand-500/15 text-brand-400 border-brand-500' : 'text-surface-200 hover:bg-surface-700 border-transparent']">
            <component :is="item.Icon" :size="16" class="flex-shrink-0"/>
            <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
          </button>
        </template>
      </template>

      <!-- LM: Tool Requests + Settings -->
      <template v-else>
        <div v-if="!collapsed" class="px-2.5 pt-4 pb-1 text-[10px] font-bold text-surface-500 uppercase tracking-widest">Tools</div>
        <div v-else class="border-t border-surface-700 my-2"/>
        <button @click="navTo(ROUTES.toolRequestsView.name)"
          :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                   isActive(ROUTES.toolRequestsView.name) ? 'bg-brand-500/15 text-brand-400 border-brand-500' : 'text-surface-200 hover:bg-surface-700 border-transparent']">
          <AlertTriangle :size="16" class="flex-shrink-0"/>
          <span v-if="!collapsed" class="truncate">Tool Requests</span>
        </button>

        <div v-if="!collapsed" class="px-2.5 pt-4 pb-1 text-[10px] font-bold text-surface-500 uppercase tracking-widest">Account</div>
        <div v-else class="border-t border-surface-700 my-2"/>
        <button @click="navTo(ROUTES.settingsView.name)"
          :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                   isActive(ROUTES.settingsView.name) ? 'bg-brand-500/15 text-brand-400 border-brand-500' : 'text-surface-200 hover:bg-surface-700 border-transparent']">
          <Settings :size="16" class="flex-shrink-0"/>
          <span v-if="!collapsed" class="truncate">Settings</span>
        </button>
      </template>
    </nav>

    <!-- Support link -->
    <div class="px-2 pb-2 border-t border-surface-700 pt-2">
      <button @click="navTo(ROUTES.supportView.name)"
        :class="['w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all border-l-2',
                isActive(ROUTES.supportView.name)
                  ? 'bg-brand-500/15 text-brand-400 border-brand-500'
                  : 'text-surface-200 hover:bg-surface-700 border-transparent']">
        <LifeBuoy :size="16" class="flex-shrink-0"/>
        <span v-if="!collapsed" class="truncate">Support</span>
      </button>
    </div>

    <!-- Theme toggle -->
    <div class="px-2 pb-2">
      <button @click="toggleTheme"
        class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all text-surface-200 hover:bg-surface-700">
        <Sun v-if="isDark" :size="16" class="flex-shrink-0"/>
        <Moon v-else :size="16" class="flex-shrink-0"/>
        <span v-if="!collapsed">{{ isDark ? 'Light Mode' : 'Dark Mode' }}</span>
      </button>
    </div>

    <!-- User chip -->
    <div class="px-3 py-3 border-t border-surface-700">
      <div class="flex items-center gap-2.5">
        <UserAvatar :initials="auth.currentUser?.avatar" size="sm"/>
        <div v-if="!collapsed" class="flex-1 min-w-0">
          <div class="text-xs font-bold text-slate-300 truncate">{{ auth.currentUser?.name }}</div>
          <div class="text-[10px] text-surface-300 capitalize">{{ auth.currentUser?.role?.replace('_',' ') }}</div>
        </div>
        <button v-if="!collapsed" @click="logout" class="text-surface-300 hover:text-red-400 transition-colors" title="Logout">
          <LogOut :size="15"/>
        </button>
      </div>
    </div>
  </aside>

  <!-- Quick-add line modal (teleported outside aside to avoid z-index issues) -->
  <Teleport to="body">
    <div v-if="addLineOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      @click.self="addLineOpen = false">
      <div class="bg-surface-900 border border-surface-600 rounded-2xl p-6 w-80 shadow-2xl">
        <h3 class="text-sm font-bold text-slate-100 mb-4">Add Line</h3>

        <div class="space-y-4 mb-5">
          <!-- Name -->
          <div>
            <label class="text-xs font-semibold text-surface-300 block mb-1.5">Name</label>
            <input v-model="addLineForm.name" placeholder="e.g. Trim Line"
              class="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-surface-400 focus:outline-none focus:border-brand-500"
              @keyup.enter="submitAddLine"/>
          </div>

          <!-- Icon picker -->
          <div>
            <label class="text-xs font-semibold text-surface-300 block mb-1.5">Icon</label>
            <div class="grid grid-cols-8 gap-1">
              <button v-for="iconName in AVAILABLE_ICONS" :key="iconName"
                type="button"
                @click="addLineForm.icon = iconName"
                :class="['p-1.5 rounded-lg transition-all flex items-center justify-center',
                         addLineForm.icon === iconName
                           ? 'bg-brand-500/25 border border-brand-500/50 text-brand-400'
                           : 'bg-surface-800 border border-surface-700 text-surface-300 hover:bg-surface-700']"
                :title="iconName">
                <component :is="iconFor(iconName)" :size="14"/>
              </button>
            </div>
          </div>

          <!-- Color -->
          <div>
            <label class="text-xs font-semibold text-surface-300 block mb-1.5">Color</label>
            <div class="flex items-center gap-2">
              <input type="color" v-model="addLineForm.color"
                class="w-10 h-10 rounded-lg border border-surface-600 bg-surface-800 cursor-pointer p-1 flex-shrink-0"/>
              <div class="flex gap-1.5 flex-wrap">
                <button v-for="c in ['#6366F1','#0EA5E9','#F59E0B','#EF4444','#10B981','#8B5CF6','#EC4899','#F97316']"
                  :key="c" type="button" @click="addLineForm.color = c"
                  class="w-6 h-6 rounded-full border-2 transition-all"
                  :style="{ background: c, borderColor: addLineForm.color === c ? '#fff' : 'transparent' }"/>
              </div>
            </div>
          </div>
        </div>

        <div class="flex gap-2 justify-end">
          <button @click="addLineOpen = false"
            class="px-4 py-2 rounded-lg text-sm font-medium text-surface-200 hover:bg-surface-700 transition-colors">
            Cancel
          </button>
          <button @click="submitAddLine" :disabled="addLineLoading"
            class="px-4 py-2 rounded-lg text-sm font-bold bg-brand-500 text-white hover:bg-brand-400 disabled:opacity-50 transition-colors">
            {{ addLineLoading ? 'Adding…' : 'Add Line' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
