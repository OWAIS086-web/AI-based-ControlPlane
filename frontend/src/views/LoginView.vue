<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput  from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'

const router = useRouter()
const auth   = useAuthStore()
const { toast } = useToast()
const email    = ref('')
const pass     = ref('')
const busy     = ref(false)
const showPass = ref(false)

async function login() {
  busy.value = true
  const err = await auth.login(email.value, pass.value)
  if (err === null) {
    toast(`Welcome back, ${auth.currentUser!.name}!`)
    router.push({ name: 'dashboard' })
  } else {
    toast(err, 'error')
    busy.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface-950 flex items-center justify-center p-4"
       style="background-image: radial-gradient(ellipse 70% 50% at 50% -5%, rgba(99,102,241,.18) 0%, transparent 70%)">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-9">
        <img src="/favicon.svg" class="w-14 h-14 rounded-2xl mb-4 shadow-xl shadow-brand-500/25 inline-block" alt="logo"/>
        <h1 class="text-2xl font-black text-slate-100">Haval ControlPlan</h1>
        <p class="text-sm text-surface-200 mt-1">Assembly Line Management System</p>
      </div>

      <!-- Card -->
      <div class="bg-surface-900 border border-surface-600 rounded-2xl p-8">
        <h2 class="text-base font-bold text-slate-100 mb-6">Sign in to your account</h2>
        <div class="space-y-4 mb-6">
          <FormField label="Email Address">
            <AppInput v-model="email" type="email" placeholder="you@factory.com" />
          </FormField>
          <FormField label="Password">
            <div class="relative">
              <AppInput v-model="pass" :type="showPass ? 'text' : 'password'" placeholder="••••••••" class="pr-9" @keydown.enter="login"/>
              <button type="button" tabindex="-1" @click="showPass = !showPass"
                class="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-200 hover:text-slate-100 transition-colors">
                <svg v-if="!showPass" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                  <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                </svg>
              </button>
            </div>
          </FormField>
        </div>
        <AppButton class="w-full justify-center py-2.5 text-sm" :loading="busy" @click="login">
          Sign In →
        </AppButton>
      </div>

      <!-- Portal switcher -->
      <div class="mt-6 text-center">
        <p class="text-surface-300 text-xs mb-3">Switch portal</p>
        <div class="flex gap-2 justify-center">
          <span class="px-4 py-2 rounded-lg text-xs font-semibold bg-brand-500/20 text-brand-300 border border-brand-500/30 cursor-default">
            Control Plan
          </span>
          <RouterLink
            to="/maintenance/login"
            class="px-4 py-2 rounded-lg text-xs font-semibold bg-surface-800 text-surface-200 border border-surface-600 hover:bg-surface-700 hover:text-slate-100 transition-colors"
          >
            Maintenance Portal
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
