<script setup lang="ts">
import { ref } from 'vue'
import { supportService } from '@/services/support.service'
import type { BugReportPayload, FeatureRequestPayload } from '@/services/support.service'
import { useToast } from '@/composables/useToast'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'
import { Bug, Lightbulb, Send, ChevronDown } from 'lucide-vue-next'

const { toast } = useToast()

type Tab = 'bug' | 'feature'
const activeTab = ref<Tab>('bug')
const loading   = ref(false)

// ─── Bug form ─────────────────────────────────────────────────────────────────
const bug = ref<BugReportPayload>({
  title: '',
  description: '',
  severity: 'medium',
  steps_to_reproduce: '',
  expected_behavior: '',
  actual_behavior: '',
})

async function submitBug() {
  if (!bug.value.title.trim())       { toast('Title is required', 'error'); return }
  if (!bug.value.description.trim()) { toast('Description is required', 'error'); return }
  loading.value = true
  try {
    const res = await supportService.reportBug(bug.value)
    toast(res.message)
    bug.value = { title: '', description: '', severity: 'medium',
                  steps_to_reproduce: '', expected_behavior: '', actual_behavior: '' }
  } catch (e: unknown) {
    toast((e as Error).message ?? 'Failed to submit', 'error')
  } finally {
    loading.value = false
  }
}

// ─── Feature form ─────────────────────────────────────────────────────────────
const feature = ref<FeatureRequestPayload>({
  title: '',
  description: '',
  priority: 'medium',
  use_case: '',
})

async function submitFeature() {
  if (!feature.value.title.trim())       { toast('Title is required', 'error'); return }
  if (!feature.value.description.trim()) { toast('Description is required', 'error'); return }
  loading.value = true
  try {
    const res = await supportService.requestFeature(feature.value)
    toast(res.message)
    feature.value = { title: '', description: '', priority: 'medium', use_case: '' }
  } catch (e: unknown) {
    toast((e as Error).message ?? 'Failed to submit', 'error')
  } finally {
    loading.value = false
  }
}

const severityOptions = [
  { value: 'low',      label: 'Low',      color: '#10B981' },
  { value: 'medium',   label: 'Medium',   color: '#F59E0B' },
  { value: 'high',     label: 'High',     color: '#F97316' },
  { value: 'critical', label: 'Critical', color: '#EF4444' },
]

const priorityOptions = [
  { value: 'low',    label: 'Low',    color: '#10B981' },
  { value: 'medium', label: 'Medium', color: '#F59E0B' },
  { value: 'high',   label: 'High',   color: '#EF4444' },
]

const severityColor = (v: string) => severityOptions.find(o => o.value === v)?.color ?? '#475569'
const priorityColor = (v: string) => priorityOptions.find(o => o.value === v)?.color ?? '#475569'
</script>

<template>
  <div class="p-8 max-w-2xl mx-auto">

    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-black text-slate-100 mb-1">Support</h1>
      <p class="text-sm text-surface-200">Report a bug or request a new feature — we review everything.</p>
    </div>

    <!-- Tab switcher -->
    <div class="flex gap-2 mb-6 p-1 bg-surface-900 border border-surface-700 rounded-xl w-fit">
      <button @click="activeTab = 'bug'"
        :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
                 activeTab === 'bug'
                   ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                   : 'text-surface-200 hover:text-slate-300']">
        <Bug :size="15"/>
        Report a Bug
      </button>
      <button @click="activeTab = 'feature'"
        :class="['flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all',
                 activeTab === 'feature'
                   ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                   : 'text-surface-200 hover:text-slate-300']">
        <Lightbulb :size="15"/>
        Request a Feature
      </button>
    </div>

    <!-- BUG FORM -->
    <AppCard v-if="activeTab === 'bug'" class="border-l-2 border-l-red-500/50">
      <h2 class="text-sm font-bold text-slate-100 mb-5 flex items-center gap-2">
        <Bug :size="15" class="text-red-400"/> Bug Report
      </h2>

      <div class="space-y-4">
        <FormField label="Title" :required="true">
          <AppInput v-model="bug.title" placeholder="Brief summary of the issue…"/>
        </FormField>

        <FormField label="Severity" :required="true">
          <div class="relative">
            <select v-model="bug.severity"
              class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm font-semibold appearance-none cursor-pointer focus:outline-none focus:border-surface-500 transition-colors pr-8"
              :style="{ color: severityColor(bug.severity) }">
              <option v-for="o in severityOptions" :key="o.value" :value="o.value"
                class="text-slate-200 bg-surface-900">
                {{ o.label }}
              </option>
            </select>
            <ChevronDown :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-300 pointer-events-none"/>
          </div>
        </FormField>

        <FormField label="Description" :required="true">
          <textarea v-model="bug.description"
            placeholder="What went wrong? Include any error messages…"
            rows="3"
            class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none"/>
        </FormField>

        <FormField label="Steps to Reproduce">
          <textarea v-model="bug.steps_to_reproduce"
            placeholder="1. Go to…&#10;2. Click on…&#10;3. See error"
            rows="3"
            class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none font-mono text-xs"/>
        </FormField>

        <div class="grid grid-cols-2 gap-4">
          <FormField label="Expected Behavior">
            <textarea v-model="bug.expected_behavior"
              placeholder="What should have happened…"
              rows="2"
              class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none"/>
          </FormField>
          <FormField label="Actual Behavior">
            <textarea v-model="bug.actual_behavior"
              placeholder="What actually happened…"
              rows="2"
              class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none"/>
          </FormField>
        </div>

        <AppButton class="w-full justify-center py-2.5 mt-2"
          style="background: rgb(239 68 68 / 0.15); color: #f87171; border: 1px solid rgb(239 68 68 / 0.3);"
          :disabled="loading" @click="submitBug">
          <Send :size="14"/>
          {{ loading ? 'Submitting…' : 'Submit Bug Report' }}
        </AppButton>
      </div>
    </AppCard>

    <!-- FEATURE FORM -->
    <AppCard v-if="activeTab === 'feature'" class="border-l-2 border-l-amber-500/50">
      <h2 class="text-sm font-bold text-slate-100 mb-5 flex items-center gap-2">
        <Lightbulb :size="15" class="text-amber-400"/> Feature Request
      </h2>

      <div class="space-y-4">
        <FormField label="Title" :required="true">
          <AppInput v-model="feature.title" placeholder="Name your feature idea…"/>
        </FormField>

        <FormField label="Priority">
          <div class="relative">
            <select v-model="feature.priority"
              class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm font-semibold appearance-none cursor-pointer focus:outline-none focus:border-surface-500 transition-colors pr-8"
              :style="{ color: priorityColor(feature.priority) }">
              <option v-for="o in priorityOptions" :key="o.value" :value="o.value"
                class="text-slate-200 bg-surface-900">
                {{ o.label }}
              </option>
            </select>
            <ChevronDown :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-300 pointer-events-none"/>
          </div>
        </FormField>

        <FormField label="Description" :required="true">
          <textarea v-model="feature.description"
            placeholder="Describe the feature you'd like to see…"
            rows="4"
            class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none"/>
        </FormField>

        <FormField label="Use Case">
          <textarea v-model="feature.use_case"
            placeholder="How would this help your workflow? Who else might benefit…"
            rows="3"
            class="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-surface-400 focus:outline-none focus:border-surface-500 transition-colors resize-none"/>
        </FormField>

        <AppButton class="w-full justify-center py-2.5 mt-2"
          style="background: rgb(245 158 11 / 0.15); color: #fbbf24; border: 1px solid rgb(245 158 11 / 0.3);"
          :disabled="loading" @click="submitFeature">
          <Send :size="14"/>
          {{ loading ? 'Submitting…' : 'Submit Feature Request' }}
        </AppButton>
      </div>
    </AppCard>

  </div>
</template>