<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { maintenanceFaultService, type FaultRecord, type FaultComment } from '@/services/maintenanceApi'
import { useMaintenanceAuthStore } from '@/stores/maintenanceAuth'
import { useToast } from '@/composables/useToast'

const route      = useRoute()
const router     = useRouter()
const auth       = useMaintenanceAuthStore()
const { toast }  = useToast()

const fault          = ref<FaultRecord | null>(null)
const comments       = ref<FaultComment[]>([])
const loading        = ref(true)
const newComment     = ref('')
const sendingComment = ref(false)
const updatingStatus = ref(false)
const editStatus     = ref('')

const SEVERITY_COLOR: Record<string, string> = {
  low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444',
}
const STATUS_COLOR: Record<string, string> = {
  open: '#ef4444', in_progress: '#f59e0b', resolved: '#10b981',
}

function statusBg(s: string) {
  return { open: '#fef2f2', in_progress: '#fffbeb', resolved: '#f0fdf4' }[s] ?? '#f9fafb'
}

function canEdit() {
  return auth.isAdmin || fault.value?.reportedBy === auth.currentUser?.id
}

function fmtDate(d: string) {
  return new Date(d).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  try {
    const id = route.params.id as string
    const [f, c] = await Promise.all([
      maintenanceFaultService.get(id),
      maintenanceFaultService.comments.list(id),
    ])
    fault.value    = f
    editStatus.value = f.status
    comments.value = c
  } catch (e: any) {
    toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function updateStatus() {
  if (!fault.value || editStatus.value === fault.value.status) return
  updatingStatus.value = true
  try {
    fault.value = await maintenanceFaultService.update(fault.value.id, { status: editStatus.value })
    toast('Status updated')
  } catch (e: any) {
    toast(e.message, 'error')
    editStatus.value = fault.value?.status ?? ''
  } finally {
    updatingStatus.value = false
  }
}

async function sendComment() {
  if (!newComment.value.trim() || !fault.value) return
  sendingComment.value = true
  try {
    const c = await maintenanceFaultService.comments.add(fault.value.id, newComment.value.trim())
    comments.value.push(c)
    newComment.value = ''
  } catch (e: any) {
    toast(e.message, 'error')
  } finally {
    sendingComment.value = false
  }
}

async function deleteComment(commentId: string) {
  if (!fault.value) return
  try {
    await maintenanceFaultService.comments.delete(fault.value.id, commentId)
    comments.value = comments.value.filter(c => c.id !== commentId)
  } catch (e: any) {
    toast(e.message, 'error')
  }
}

onMounted(load)
</script>

<template>
  <div class="m-fault-detail">

    <button class="m-back-btn" @click="router.back()">
      <i class="fa-solid fa-arrow-left"></i> Back to Faults
    </button>

    <div v-if="loading" class="m-loading">
      <i class="fa-solid fa-spinner fa-spin"></i> Loading fault…
    </div>

    <template v-else-if="fault">
      <div class="m-detail-grid">

        <!-- Main content -->
        <div style="display:flex;flex-direction:column;gap:1.25rem;">

          <!-- Fault info card -->
          <div class="m-card">
            <div class="m-card-body">
              <div class="m-fault-title-row">
                <h1 class="m-fault-title">{{ fault.title }}</h1>
                <div class="m-badges">
                  <span
                    class="m-badge"
                    :style="{ background: SEVERITY_COLOR[fault.severity] + '22', color: SEVERITY_COLOR[fault.severity] }"
                  >{{ fault.severity }}</span>
                  <span
                    class="m-badge"
                    :style="{ background: statusBg(fault.status), color: STATUS_COLOR[fault.status] }"
                  >{{ fault.status.replace('_', ' ') }}</span>
                </div>
              </div>
              <p class="m-fault-desc">{{ fault.description }}</p>
            </div>
          </div>

          <!-- Comments card -->
          <div class="m-card">
            <div class="m-card-body">
              <h3 class="m-section-title">
                <i class="fa-solid fa-comments" style="color:#f59e0b;margin-right:0.5rem"></i>
                Comments ({{ comments.length }})
              </h3>

              <div class="m-comment-list" v-if="comments.length > 0">
                <div v-for="c in comments" :key="c.id" class="m-comment">
                  <div class="m-comment-avatar">{{ c.authorName?.[0]?.toUpperCase() }}</div>
                  <div style="flex:1;min-width:0">
                    <div class="m-comment-meta">
                      <span class="m-comment-author">{{ c.authorName }}</span>
                      <span class="m-comment-time">{{ fmtDate(c.createdAt) }}</span>
                    </div>
                    <p class="m-comment-body">{{ c.body }}</p>
                  </div>
                  <button
                    v-if="auth.isAdmin || c.userId === auth.currentUser?.id"
                    class="m-comment-delete"
                    title="Delete comment"
                    @click="deleteComment(c.id)"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </div>

              <div v-else class="m-empty-comments">
                <i class="fa-regular fa-comment-dots" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>
                No comments yet. Be the first to add one.
              </div>

              <!-- Add comment -->
              <div class="m-comment-form">
                <textarea
                  v-model="newComment"
                  class="m-textarea"
                  rows="2"
                  placeholder="Add a comment… (Ctrl+Enter to send)"
                  @keydown.ctrl.enter="sendComment"
                ></textarea>
                <button
                  class="m-btn m-btn-primary"
                  style="align-self:flex-end;white-space:nowrap"
                  :disabled="sendingComment || !newComment.trim()"
                  @click="sendComment"
                >
                  <i v-if="sendingComment" class="fa-solid fa-spinner fa-spin"></i>
                  <i v-else class="fa-solid fa-paper-plane"></i>
                  Send
                </button>
              </div>
            </div>
          </div>

        </div>

        <!-- Sidebar -->
        <div class="m-detail-sidebar">

          <!-- Fault details -->
          <div class="m-card">
            <div class="m-card-body">
              <p class="m-detail-label">Fault Details</p>
              <dl class="m-meta-list">
                <div class="m-meta-item">
                  <dt>Location</dt>
                  <dd>{{ fault.location || '—' }}</dd>
                </div>
                <div class="m-meta-item">
                  <dt>Reported by</dt>
                  <dd>{{ fault.reporterName }}</dd>
                </div>
                <div class="m-meta-item" v-if="fault.assigneeName">
                  <dt>Assigned to</dt>
                  <dd>{{ fault.assigneeName }}</dd>
                </div>
                <div class="m-meta-item">
                  <dt>Reported on</dt>
                  <dd style="font-size:0.875rem;font-weight:400">{{ fmtDate(fault.createdAt) }}</dd>
                </div>
                <div class="m-meta-item" v-if="fault.resolvedAt">
                  <dt>Resolved on</dt>
                  <dd class="resolved" style="font-size:0.875rem;font-weight:400">{{ fmtDate(fault.resolvedAt) }}</dd>
                </div>
              </dl>
            </div>
          </div>

          <!-- Status update (if can edit) -->
          <div class="m-card" v-if="canEdit()">
            <div class="m-card-body">
              <p class="m-detail-label">Update Status</p>
              <div class="m-status-form">
                <label>Current Status</label>
                <select v-model="editStatus" class="m-select" :disabled="updatingStatus">
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
                <button
                  class="m-btn m-btn-primary"
                  style="margin-top:0.5rem;width:100%"
                  :disabled="updatingStatus || editStatus === fault.status"
                  @click="updateStatus"
                >
                  <i v-if="updatingStatus" class="fa-solid fa-spinner fa-spin"></i>
                  <i v-else class="fa-solid fa-floppy-disk"></i>
                  {{ updatingStatus ? 'Saving…' : 'Save Status' }}
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </template>

  </div>
</template>

<style scoped src="@/styles/pages/maintenance-fault-detail.css"></style>
