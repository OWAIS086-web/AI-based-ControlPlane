// ─── Shared re-exports ────────────────────────────────────────────────────────
// Line and LineType are now dynamic (fetched from the API via useLinesStore).
// Re-export them here so existing imports of Line from '@/stores/app' keep working.

export type { Line, LineType, LineTypeWithLines } from '@/stores/lines'
export { useLinesStore }                          from '@/stores/lines'

export type { User }                                      from '@/stores/auth'
export type { CarModel }                                  from '@/stores/carModels'
export type { Station, Process, ProcessVersion, DiffRow } from '@/stores/stations'
export type { MigrationRecord }                           from '@/stores/migrations'
export type { AuditEntry }                                from '@/stores/audit'
