<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMaintenanceAuthStore } from '@/stores/maintenanceAuth'
import { useToast } from '@/composables/useToast'

const router     = useRouter()
const auth       = useMaintenanceAuthStore()
const { toast }  = useToast()

const email    = ref('')
const password = ref('')
const busy     = ref(false)
const showPass = ref(false)

async function login() {
  if (!email.value || !password.value) { toast('Email and password required', 'error'); return }
  busy.value = true
  const err  = await auth.login(email.value, password.value)
  if (err === null) {
    toast(`Welcome, ${auth.currentUser!.name}!`)
    router.push({ name: 'maintenance-dashboard' })
  } else {
    toast(err, 'error')
    busy.value = false
  }
}
</script>

<template>
  <div class="m-login-page">
    <div class="m-login-card">

      <!-- Logo -->
      <div class="m-login-logo">
        <div class="m-login-logo-icon">
          <i class="fa-solid fa-wrench"></i>
        </div>
        <h1>Maintenance Portal</h1>
        <p>Haval Fault Management System</p>
      </div>

      <!-- Form card -->
      <div class="m-login-form-card">
        <h2>Sign in to your account</h2>

        <div class="m-form-group">
          <label for="email">Email Address</label>
          <input
            id="email"
            v-model="email"
            type="email"
            class="m-form-input"
            placeholder="you@haval.com"
            autocomplete="email"
            @keydown.enter="login"
          />
        </div>

        <div class="m-form-group">
          <label for="password">Password</label>
          <div class="m-password-wrapper">
            <input
              id="password"
              v-model="password"
              :type="showPass ? 'text' : 'password'"
              class="m-form-input"
              placeholder="••••••••"
              autocomplete="current-password"
              @keydown.enter="login"
            />
            <button type="button" class="m-password-toggle" @click="showPass = !showPass" tabindex="-1">
              <i :class="showPass ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
            </button>
          </div>
        </div>

        <button class="m-btn-primary" :disabled="busy" @click="login">
          <i v-if="busy" class="fa-solid fa-spinner fa-spin"></i>
          <i v-else class="fa-solid fa-right-to-bracket"></i>
          {{ busy ? 'Signing in…' : 'Sign In' }}
        </button>
      </div>

      <div class="m-portal-switch">
        <p>Switch portal</p>
        <div class="m-portal-btns">
          <RouterLink to="/login" class="m-portal-btn">
            <i class="fa-solid fa-chart-line"></i>
            Control Plan
          </RouterLink>
          <span class="m-portal-btn m-portal-btn--active">
            <i class="fa-solid fa-wrench"></i>
            Maintenance
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped src="@/styles/pages/maintenance-login.css"></style>
