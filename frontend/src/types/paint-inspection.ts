export interface InspectionDefect {
  id?: number
  inspection_id?: number
  serial_no: number
  name: string
  total_qty: number | null
  let_go_qty: number | null
  repair_qty: number | null
  remarks: string | null
  created_at?: string
  updated_at?: string
}

export interface VehiclePart {
  id?: number
  inspection_id?: number
  part_code: string
  part_name: string
  position: 'front' | 'rear' | 'left' | 'right' | 'top' | 'hood' | 'roof' | 'trunk' | 'door-left-front' | 'door-left-rear' | 'door-right-front' | 'door-right-rear' | 'fender-left' | 'fender-right' | 'bumper-front' | 'bumper-rear'
  annotation: string | null
  created_at?: string
}

export interface PaintInspection {
  id: number
  inspection_date: string
  painting_date: string
  oven_out_time: string | null
  color: string
  vin_no: string
  total_problems: number
  checked_by: string | null
  confirmed_by: string | null
  approved_by: string | null
  created_by_id: string
  created_at: string
  updated_at: string
  defects: InspectionDefect[]
  vehicle_parts: VehiclePart[]
}

export interface PaintInspectionCreate {
  inspection_date: string
  painting_date: string
  oven_out_time?: string | null
  color: string
  vin_no: string
  checked_by?: string | null
  confirmed_by?: string | null
  approved_by?: string | null
  defects: Omit<InspectionDefect, 'id' | 'inspection_id' | 'created_at' | 'updated_at'>[]
  vehicle_parts: Omit<VehiclePart, 'id' | 'inspection_id' | 'created_at'>[]
}

export interface PaintInspectionUpdate {
  inspection_date: string
  painting_date: string
  oven_out_time?: string | null
  color: string
  vin_no: string
  checked_by?: string | null
  confirmed_by?: string | null
  approved_by?: string | null
  defects: Omit<InspectionDefect, 'id' | 'inspection_id' | 'created_at' | 'updated_at'>[]
  vehicle_parts: Omit<VehiclePart, 'id' | 'inspection_id' | 'created_at'>[]
}

export interface PaintInspectionListResponse {
  items: PaintInspection[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PaintInspectionFilter {
  page?: number
  page_size?: number
  vin_no?: string
  color?: string
  inspection_date_from?: string
  inspection_date_to?: string
  checked_by?: string
}

export const DEFAULT_DEFECT_TYPES = [
  'Black Dust',
  'Major Dust',
  'Minor Dust',
  'Dent',
  'Sag',
  'Orange Peel',
  'Glassing',
  'Less paint',
  'Craters',
  'Others',
] as const

export type DefectType = (typeof DEFAULT_DEFECT_TYPES)[number]
