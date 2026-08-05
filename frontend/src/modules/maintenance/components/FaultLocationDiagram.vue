<script setup lang="ts">
import { ref } from 'vue'
import type { FaultRecord } from '@/services/maintenanceApi'

interface CarPart {
  id: string
  name: string
  imagePath: string
  x: number
  y: number
  width: number
  height: number
}

interface Props {
  faults: FaultRecord[]
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), { readonly: true })

const emit = defineEmits<{
  partClick: [partId: string, partName: string, faults: FaultRecord[]]
}>()

const hoveredPart = ref<string | null>(null)

// Same 15 car parts from the paint-inspection Vehicle3DViewer
const carParts: CarPart[] = [
  { id: 'left-front-fender',  name: 'Left Front Fender',         imagePath: '/car/left front fender.png',              x: 5,  y: 5,  width: 18, height: 20 },
  { id: 'left-front-door',    name: 'Left Front Door Shell',      imagePath: '/car/Left Front  Door Shell Back.png',    x: 5,  y: 25, width: 18, height: 20 },
  { id: 'right-front-fender', name: 'Right Front Fender',         imagePath: '/car/right front fender.png',             x: 77, y: 5,  width: 18, height: 20 },
  { id: 'right-front-door',   name: 'Right Front Door Shell',     imagePath: '/car/Right Front Door Shell.png',         x: 77, y: 25, width: 18, height: 20 },
  { id: 'left-rear-door',     name: 'Left Rear Door Shell',       imagePath: '/car/Left Door Shell Back.png',           x: 5,  y: 43, width: 18, height: 16 },
  { id: 'left-rear-quarter',  name: 'Left Rear Quarter Panel',    imagePath: '/car/Left Rear Quarter Pannel.png',       x: 5,  y: 61, width: 18, height: 12 },
  { id: 'right-rear-door',    name: 'Right Rear Door Shell',      imagePath: '/car/Right Door Shell Back.png',          x: 77, y: 43, width: 18, height: 16 },
  { id: 'right-rear-quarter', name: 'Right Rear Quarter Panel',   imagePath: '/car/Right Rear Quarter Pannel.png',      x: 77, y: 61, width: 18, height: 12 },
  { id: 'front-grille',       name: 'Front Grille Assembly',      imagePath: '/car/Front Grille.png',                   x: 25, y: 2,  width: 50, height: 12 },
  { id: 'bonnet',             name: 'Hood Panel (Bonnet)',         imagePath: '/car/bonnet.png',                         x: 25, y: 16, width: 50, height: 14 },
  { id: 'roof',               name: 'Roof Outer Panel',           imagePath: '/car/roof.png',                           x: 25, y: 32, width: 50, height: 14 },
  { id: 'rear-spoiler',       name: 'Rear Spoiler Upper',         imagePath: '/car/Rear spoiler.png',                   x: 30, y: 48, width: 40, height: 10 },
  { id: 'tailgate',           name: 'Tailgate Assembly',          imagePath: '/car/Tailgate.png',                       x: 25, y: 60, width: 50, height: 12 },
  { id: 'bumper',             name: 'Rear Bumper Cover',          imagePath: '/car/Bumber.png',                         x: 25, y: 74, width: 50, height: 12 },
  { id: 'rear-diffuser',      name: 'Rear Lower Diffuser',        imagePath: '/car/Rear lower Diffuser.png',            x: 25, y: 88, width: 50, height: 12 },
]

function getFaultsForPart(part: CarPart): FaultRecord[] {
  const searchTerms = [part.id.toLowerCase(), part.name.toLowerCase()]
  return props.faults.filter(f => {
    if (!f.location) return false
    const loc = f.location.toLowerCase()
    return searchTerms.some(term => loc.includes(term) || term.includes(loc))
  })
}

function severityColor(severity: string): string {
  return { low: '#10b981', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' }[severity] ?? '#6b7280'
}

function handlePartClick(part: CarPart) {
  if (props.readonly) return
  const partFaults = getFaultsForPart(part)
  emit('partClick', part.id, part.name, partFaults)
}

function handleDiagramClick(event: MouseEvent) {
  const container = event.currentTarget as HTMLDivElement
  const rect = container.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100
  const clicked = carParts.find(p => x >= p.x && x <= p.x + p.width && y >= p.y && y <= p.y + p.height)
  if (clicked) handlePartClick(clicked)
}
</script>

<template>
  <div class="fld-viewer">
    <!-- Interactive Diagram -->
    <div class="fld-diagram" @click="handleDiagramClick">
      <div class="fld-grid">
        <div
          v-for="part in carParts"
          :key="part.id"
          class="fld-part"
          :style="{
            left:   part.x + '%',
            top:    part.y + '%',
            width:  part.width + '%',
            height: part.height + '%',
          }"
          @mouseenter="hoveredPart = part.id"
          @mouseleave="hoveredPart = null"
          @click.stop="handlePartClick(part)"
        >
          <!-- Part image -->
          <img
            :src="part.imagePath"
            :alt="part.name"
            class="fld-img"
            :class="{ 'has-faults': getFaultsForPart(part).length > 0 }"
          />

          <!-- Overlay -->
          <div
            class="fld-overlay"
            :class="{
              'has-faults':  getFaultsForPart(part).length > 0,
              'hovered':     hoveredPart === part.id,
              'interactive': !readonly,
            }"
          >
            <!-- Fault count badge -->
            <div v-if="getFaultsForPart(part).length > 0" class="fld-badge">
              {{ getFaultsForPart(part).length }}
            </div>

            <!-- Arrow + label box on hover -->
            <div
              v-if="hoveredPart === part.id && getFaultsForPart(part).length > 0"
              class="fld-pointer"
              :class="part.x > 50 ? 'fld-pointer-left' : 'fld-pointer-right'"
            >
              <svg
                class="fld-arrow"
                viewBox="0 0 200 100"
                preserveAspectRatio="none"
                :style="part.x > 50 ? 'transform: scaleX(-1)' : ''"
              >
                <defs>
                  <marker id="fld-arrow-head" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <polygon points="0 0, 10 3, 0 6" fill="#d97706" />
                  </marker>
                </defs>
                <path
                  d="M 0 50 Q 60 50 160 30"
                  stroke="#d97706"
                  stroke-width="2.5"
                  fill="none"
                  marker-end="url(#fld-arrow-head)"
                  class="fld-arrow-path"
                />
              </svg>

              <div class="fld-label-box">
                <div class="fld-label-title">{{ part.name }}</div>
                <div
                  v-for="fault in getFaultsForPart(part).slice(0, 3)"
                  :key="fault.id"
                  class="fld-label-fault"
                >
                  <span
                    class="fld-severity-dot"
                    :style="{ background: severityColor(fault.severity) }"
                  ></span>
                  <span class="fld-fault-title">{{ fault.title }}</span>
                </div>
                <div
                  v-if="getFaultsForPart(part).length > 3"
                  class="fld-label-more"
                >
                  +{{ getFaultsForPart(part).length - 3 }} more
                </div>
              </div>
            </div>

            <!-- Part label on hover (no faults) -->
            <div
              v-if="hoveredPart === part.id && getFaultsForPart(part).length === 0"
              class="fld-part-label"
            >
              {{ part.name }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="fld-legend">
      <div class="fld-legend-item">
        <span class="fld-legend-dot" style="background: #ef4444; box-shadow: 0 0 6px #ef444466"></span>
        Has faults
      </div>
      <div class="fld-legend-item">
        <span class="fld-legend-dot" style="background: #d1d5db"></span>
        No faults
      </div>
    </div>
  </div>
</template>

<style scoped>
.fld-viewer {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.fld-diagram {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.5rem;
  cursor: default;
}

.fld-grid {
  position: relative;
  width: 100%;
  max-width: 820px;
  aspect-ratio: 0.75;
  margin: 0 auto;
}

.fld-part {
  position: absolute;
  cursor: pointer;
  transition: transform 0.18s ease, z-index 0s;
}

.fld-part:hover { transform: scale(1.04); z-index: 10; }

.fld-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 0.25rem;
  border: 1.5px solid #e5e7eb;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: white;
}

.fld-img.has-faults {
  border: 2px solid #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.25), 0 2px 8px rgba(239, 68, 68, 0.15);
}

/* Overlay */
.fld-overlay {
  position: absolute;
  inset: 0;
  border-radius: 0.25rem;
  opacity: 0;
  transition: opacity 0.18s, background 0.18s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fld-overlay.interactive { cursor: pointer; }
.fld-overlay.hovered { opacity: 1; background: rgba(245, 158, 11, 0.12); }
.fld-overlay.has-faults { background: rgba(239, 68, 68, 0.08); }
.fld-overlay.has-faults.hovered { background: rgba(239, 68, 68, 0.18); }

/* Fault badge */
.fld-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ef4444;
  color: #fff;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 0.6875rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.45);
  border: 2px solid white;
  z-index: 20;
}

/* Arrow pointer */
.fld-pointer {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 160px;
  height: 90px;
  z-index: 30;
  pointer-events: none;
}

.fld-pointer-right {
  left: calc(100% + 4px);
}

.fld-pointer-left {
  right: calc(100% + 4px);
}

.fld-arrow {
  width: 100%;
  height: 100%;
}

.fld-arrow-path {
  animation: fld-pulse 2s ease-in-out infinite;
}

@keyframes fld-pulse {
  0%, 100% { opacity: 1; stroke-width: 2.5; }
  50%       { opacity: 0.55; stroke-width: 3.5; }
}

/* Label box */
.fld-label-box {
  position: absolute;
  top: 0;
  white-space: nowrap;
  background: #fff;
  border: 1.5px solid #fde68a;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  min-width: 140px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 40;
}

.fld-pointer-right .fld-label-box { left: 100%; margin-left: 4px; }
.fld-pointer-left  .fld-label-box { right: 100%; margin-right: 4px; }

.fld-label-title {
  font-size: 0.6875rem;
  font-weight: 700;
  color: #d97706;
  margin-bottom: 0.375rem;
  border-bottom: 1px solid #fef3c7;
  padding-bottom: 0.25rem;
}

.fld-label-fault {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0.2rem 0;
}

.fld-severity-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.fld-fault-title {
  font-size: 0.6875rem;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.fld-label-more {
  font-size: 0.625rem;
  color: #9ca3af;
  margin-top: 0.25rem;
}

/* Part label (no faults hover) */
.fld-part-label {
  background: rgba(17, 24, 39, 0.8);
  color: #fff;
  padding: 0.375rem 0.625rem;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
  max-width: 90%;
  text-align: center;
}

/* Legend */
.fld-legend {
  display: flex;
  gap: 1.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}

.fld-legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fld-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
