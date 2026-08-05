import { piApi } from './paintInspectionApi'
import type {
  PaintInspection,
  PaintInspectionCreate,
  PaintInspectionUpdate,
  PaintInspectionListResponse,
  PaintInspectionFilter,
} from '@/types/paint-inspection'

export const paintInspectionService = {
  async create(data: PaintInspectionCreate): Promise<PaintInspection> {
    return piApi.post<PaintInspection>('', data)
  },

  async getList(filters?: PaintInspectionFilter): Promise<PaintInspectionListResponse> {
    const params = new URLSearchParams()
    if (filters) {
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', filters.page_size.toString())
      if (filters.vin_no) params.append('vin_no', filters.vin_no)
      if (filters.color) params.append('color', filters.color)
      if (filters.inspection_date_from) params.append('inspection_date_from', filters.inspection_date_from)
      if (filters.inspection_date_to) params.append('inspection_date_to', filters.inspection_date_to)
      if (filters.checked_by) params.append('checked_by', filters.checked_by)
    }
    const qs = params.toString()
    return piApi.get<PaintInspectionListResponse>(qs ? `?${qs}` : '')
  },

  async getById(id: number): Promise<PaintInspection> {
    return piApi.get<PaintInspection>(`/${id}`)
  },

  async update(id: number, data: PaintInspectionUpdate): Promise<PaintInspection> {
    return piApi.put<PaintInspection>(`/${id}`, data)
  },

  async delete(id: number): Promise<void> {
    return piApi.delete(`/${id}`)
  },

  async search(query: string): Promise<PaintInspection[]> {
    return piApi.get<PaintInspection[]>(`/search/query?q=${encodeURIComponent(query)}`)
  },
}
