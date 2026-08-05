<script setup lang="ts">
import { ref } from 'vue'
import type { VehiclePart } from '@/types/paint-inspection'

interface Props {
  vehicleParts: Omit<VehiclePart, 'id' | 'inspection_id' | 'created_at'>[]
  defects?: Array<{
    name: string
    total_qty: number | null
    repair_qty: number | null
  }>
  readonly?: boolean
}

interface DefectOnPart {
  partPosition: string
  partName: string
  defectName: string
  quantity: number
  repairQty?: number
}

interface CarPart {
  id: string
  name: string
  imagePath: string
  x: number
  y: number
  width: number
  height: number
}

const props = withDefaults(defineProps<Props>(), { readonly: false })

const emit = defineEmits<{
  addDefect: [defect: DefectOnPart]
  removeDefect: [partPosition: string, defectName: string]
  updateDefect: [defect: DefectOnPart]
}>()

const showDefectModal = ref(false)
const selectedPartInfo = ref<{ position: string; name: string } | null>(null)
const defectName = ref('')
const defectQuantity = ref(1)
const hoveredPart = ref<string | null>(null)

const carParts: CarPart[] = [
  { id: 'left-front-fender', name: 'Left Front Fender', imagePath: '/car/left front fender.png', x: 5, y: 5, width: 18, height: 20 },
  { id: 'left-front-door', name: 'Left Front Door Shell', imagePath: '/car/Left Front  Door Shell Back.png', x: 5, y: 25, width: 18, height: 20 },
  { id: 'right-front-fender', name: 'Right Front Fender', imagePath: '/car/right front fender.png', x: 77, y: 5, width: 18, height: 20 },
  { id: 'right-front-door', name: 'Right Front Door Shell', imagePath: '/car/Right Front Door Shell.png', x: 77, y: 25, width: 18, height: 20 },
  { id: 'left-rear-door', name: 'Left Rear Door Shell', imagePath: '/car/Left Door Shell Back.png', x: 5, y: 43, width: 18, height: 16 },
  { id: 'left-rear-quarter', name: 'Left Rear Quarter Panel', imagePath: '/car/Left Rear Quarter Pannel.png', x: 5, y: 61, width: 18, height: 12 },
  { id: 'right-rear-door', name: 'Right Rear Door Shell', imagePath: '/car/Right Door Shell Back.png', x: 77, y: 43, width: 18, height: 16 },
  { id: 'right-rear-quarter', name: 'Right Rear Quarter Panel', imagePath: '/car/Right Rear Quarter Pannel.png', x: 77, y: 61, width: 18, height: 12 },
  { id: 'front-grille', name: '1. Front Grille Assembly', imagePath: '/car/Front Grille.png', x: 25, y: 2, width: 50, height: 12 },
  { id: 'bonnet', name: '2. Hood Panel (Bonnet)', imagePath: '/car/bonnet.png', x: 25, y: 16, width: 50, height: 14 },
  { id: 'roof', name: '3. Roof Outer Panel', imagePath: '/car/roof.png', x: 25, y: 32, width: 50, height: 14 },
  { id: 'rear-spoiler', name: '4. Rear Spoiler Upper', imagePath: '/car/Rear spoiler.png', x: 30, y: 48, width: 40, height: 10 },
  { id: 'tailgate', name: '5. Tailgate Assembly', imagePath: '/car/Tailgate.png', x: 25, y: 60, width: 50, height: 12 },
  { id: 'bumper', name: '6. Rear Bumper Cover', imagePath: '/car/Bumber.png', x: 25, y: 74, width: 50, height: 12 },
  { id: 'rear-diffuser', name: '7. Rear Lower Diffuser', imagePath: '/car/Rear lower Diffuser.png', x: 25, y: 88, width: 50, height: 12 },
]

const selectPart = (partId: string, partName: string) => {
  if (props.readonly) return
  selectedPartInfo.value = { position: partId, name: partName }
  showDefectModal.value = true
  hoveredPart.value = null
}

function handleTouchStart(partId: string) {
  hoveredPart.value = partId
}

const getDefectsForPart = (partId: string): DefectOnPart[] => {
  const matchingParts = props.vehicleParts.filter(
    (vp) => vp.part_code === partId && vp.annotation && vp.annotation.trim() !== ''
  )
  return matchingParts.map((part) => {
    const matchingDefect = props.defects?.find((d) => d.name === part.annotation)
    return {
      partPosition: part.position,
      partName: part.part_name,
      defectName: part.annotation || '',
      quantity: matchingDefect?.total_qty || 1,
      repairQty: matchingDefect?.repair_qty || 0,
    }
  })
}

const addDefect = () => {
  if (!selectedPartInfo.value || !defectName.value.trim()) return
  emit('addDefect', {
    partPosition: selectedPartInfo.value.position,
    partName: selectedPartInfo.value.name,
    defectName: defectName.value,
    quantity: defectQuantity.value,
  })
  defectName.value = ''
  defectQuantity.value = 1
  showDefectModal.value = false
}
</script>

<template>
  <div class="vehicle-3d-viewer">
    <div class="viewer-header">
      <h3>Vehicle Diagram - Click on Parts to Add Defects</h3>
      <p class="text-sm text-gray-600">Click on any car part to add or view defects</p>
    </div>

    <div class="diagram-container">
      <div class="vehicle-diagram-grid">
        <div
          v-for="part in carParts"
          :key="part.id"
          class="part-wrapper"
          :style="{
            gridColumn: `${Math.round(part.x / 10)} / span ${Math.round(part.width / 10)}`,
            gridRow: `${Math.round(part.y / 10)} / span ${Math.round(part.height / 10)}`,
          }"
        >
          <img
            :src="part.imagePath"
            :alt="part.name"
            class="part-image"
            :class="{ 'has-defects': getDefectsForPart(part.id).length > 0 }"
          />

          <div
            class="part-overlay"
            :class="[{
              'has-defects': getDefectsForPart(part.id).length > 0,
              'hovered': hoveredPart === part.id,
            }]"
            @mouseenter="hoveredPart = part.id"
            @mouseleave="hoveredPart = null"
            @touchstart.passive="handleTouchStart(part.id)"
            @click.stop="!readonly && selectPart(part.id, part.name)"
          >
            <!-- Always visible on touch; hover-visible on desktop -->
            <div v-if="getDefectsForPart(part.id).length > 0" class="defect-badge">
              {{ getDefectsForPart(part.id).length }}
            </div>

            <div v-if="getDefectsForPart(part.id).length > 0 && hoveredPart === part.id" class="defect-pointer">
              <svg class="defect-arrow-line" viewBox="0 0 200 100" preserveAspectRatio="none">
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <polygon points="0 0, 10 3, 0 6" fill="#15803d" />
                  </marker>
                </defs>
                <path d="M 0 50 Q 50 50 150 30" stroke="#15803d" stroke-width="2" fill="none" marker-end="url(#arrowhead)" />
              </svg>
              <div class="defect-label-box">
                <div v-for="(defect, idx) in getDefectsForPart(part.id)" :key="idx" class="defect-label-item">
                  <span class="defect-label-name">{{ defect.defectName }}</span>
                  <span class="defect-label-qty">
                    <span class="qty-label">Total:</span>
                    <span class="qty-value">{{ defect.quantity }}</span>
                  </span>
                </div>
              </div>
            </div>

            <div v-if="hoveredPart === part.id" class="part-label">{{ part.name }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Defect Modal -->
    <div v-if="showDefectModal && !readonly" class="modal-overlay" @click.self="showDefectModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h4>Add Defect to {{ selectedPartInfo?.name }}</h4>
          <button @click="showDefectModal = false" class="btn-close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Defect Name *</label>
            <input
              v-model="defectName"
              type="text"
              placeholder="e.g., Dust, Scratch, Paint Run"
              class="form-input"
              @keyup.enter="addDefect"
              autofocus
            />
          </div>
          <div class="form-group">
            <label>Quantity *</label>
            <input v-model.number="defectQuantity" type="number" min="1" class="form-input" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showDefectModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="addDefect" class="btn btn-primary" :disabled="!defectName.trim()">
            Add Defect
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vehicle-3d-viewer {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.viewer-header { display: flex; flex-direction: column; gap: 0.25rem; }

.viewer-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.diagram-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.vehicle-diagram-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  grid-template-rows: repeat(10, 1fr);
  gap: 0.5rem;
  width: 100%;
  max-width: 900px;
  aspect-ratio: 0.8;
  margin: 0 auto;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 0.375rem;
  padding: 1rem;
}

.part-wrapper {
  position: relative;
  overflow: visible;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.part-wrapper:hover { transform: scale(1.02); z-index: 10; }

.part-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 0.25rem;
  border: 1px solid #d1d5db;
  transition: all 0.2s ease;
}

.part-image.has-defects {
  border: 3px solid #15803d;
  box-shadow: 0 0 0 2px rgba(21, 128, 61, 0.3);
}

.part-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.part-overlay:hover,
.part-overlay.hovered {
  opacity: 1;
  background: rgba(59, 130, 246, 0.2);
}

.part-overlay.has-defects { background: rgba(239, 68, 68, 0.1); }
.part-overlay.has-defects:hover,
.part-overlay.has-defects.hovered { background: rgba(239, 68, 68, 0.2); }

.defect-badge {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  background: #ef4444;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 20;
}

.defect-pointer {
  position: absolute;
  top: 50%;
  right: -150px;
  transform: translateY(-50%);
  width: 150px;
  height: 100px;
  z-index: 30;
  pointer-events: none;
}

.defect-arrow-line {
  width: 100%;
  height: 100%;
  animation: pulse-arrow 2s infinite;
}

.defect-label-box {
  position: absolute;
  top: -10px;
  right: 0;
  background: white;
  border: 2px solid #15803d;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  min-width: 120px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 31;
}

.defect-label-item {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.75rem;
  margin: 0.25rem 0;
  flex-wrap: wrap;
}

.defect-label-name { font-weight: 600; color: #15803d; min-width: 80px; }

.defect-label-qty {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  background: #f0fdf4;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  border: 1px solid #bbf7d0;
}

.qty-label { font-weight: 600; color: #059669; font-size: 0.65rem; }
.qty-value { color: #059669; font-weight: 700; }

@keyframes pulse-arrow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.part-label {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  width: 90%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #000;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: #6b7280;
  cursor: pointer;
}

.btn-close:hover { color: #1f2937; }

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }

.form-group label { font-size: 0.875rem; font-weight: 500; color: #000; }

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #000;
  background: #fff;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.modal-footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #d1d5db; cursor: not-allowed; }

.btn-secondary { background: #e5e7eb; color: #374151; }
.btn-secondary:hover { background: #d1d5db; }

/* Tablet: reduce padding so the 10×10 grid gets more room */
@media (max-width: 1024px) {
  .vehicle-3d-viewer   { padding: 1rem; gap: 1rem; }
  .diagram-container   { padding: 0.75rem; }
  .vehicle-diagram-grid { padding: 0.5rem; gap: 0.25rem; }
  .modal-body          { padding: 1.25rem; }
  .modal-footer        { padding: 1.25rem; }
  .btn                 { padding: 0.75rem 1.25rem; min-height: 44px; font-size: 0.9375rem; }
  .form-input          { padding: 0.75rem; font-size: 1rem; min-height: 44px; }
}

/* Touch devices: always show overlay & badge so users see interaction affordance */
@media (hover: none) {
  .part-overlay { opacity: 1; background: rgba(59, 130, 246, 0.04); }
  .part-overlay.has-defects { background: rgba(239, 68, 68, 0.06); }
  .part-overlay:active { background: rgba(59, 130, 246, 0.18) !important; }
  .defect-badge { top: 2px; right: 2px; width: 20px; height: 20px; font-size: 0.6875rem; }
  .part-label { font-size: 0.6875rem; padding: 0.25rem 0.5rem; white-space: normal; max-width: 90px; text-align: center; }
}

/* Portrait phone — make diagram horizontally scrollable rather than breaking it */
@media (max-width: 500px) {
  .diagram-container { overflow-x: auto; }
  .vehicle-diagram-grid { min-width: 320px; }
}
</style>
