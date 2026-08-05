import { api } from '@/services/api'
import type { PaginatedResponse } from '@/services/api'
import type { ApiUser } from '@/services/auth.service'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiDiffSheet {
  sheet_name: string
  status: string
  cell_changes: {
    modified: Record<string, { previous: string; current: string }>
    added:    Record<string, { value: string }>
    removed:  Record<string, { value: string }>
  }
  summary: { total_modified: number; total_added: number; total_removed: number }
  shape_changes: { added: string[]; removed: string[] }
}

export interface ApiDiff {
  sheets: ApiDiffSheet[]
  summary: Record<string, number>
}

export interface ApiProcessVersion {
  id: string
  processId: string
  version: string
  fileUrl: string
  fileName: string | null
  fileSize: number         // bytes
  commitMessage: string
  changes: number
  uploadedBy: string       // User ID
  uploader?: ApiUser
  diff: string             // JSON-encoded ApiDiff
  extractedData: any
  createdAt: string
}

export interface VersionCompareResult {
  v1: ApiProcessVersion
  v2: ApiProcessVersion
  diff: ApiDiff
  summary: {
    added: number
    modified: number
    removed: number
  }
}

export interface VersionListParams {
  page?: number
  limit?: number
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const versionsService = {
  async list(
    processId: string,
    params: VersionListParams = {},
  ): Promise<PaginatedResponse<ApiProcessVersion>> {
    const qs = new URLSearchParams()
    qs.set('page',  String(params.page  ?? 1))
    qs.set('limit', String(params.limit ?? 100))
    return api.get<PaginatedResponse<ApiProcessVersion>>(
      `/processes/${processId}/versions?${qs}`,
    )
  },

  async get(processId: string, versionId: string): Promise<ApiProcessVersion> {
    return api.get<ApiProcessVersion>(`/processes/${processId}/versions/${versionId}`)
  },

  async upload(processId: string, file: File, commitMessage: string): Promise<ApiProcessVersion> {
    const form = new FormData()
    form.append('file', file)
    form.append('commitMessage', commitMessage)
    return api.post<ApiProcessVersion>(`/processes/${processId}/versions`, form)
  },

  async compare(
    processId: string,
    v1Id: string,
    v2Id: string,
  ): Promise<VersionCompareResult> {
    return api.get<VersionCompareResult>(
      `/processes/${processId}/versions/compare?v1=${v1Id}&v2=${v2Id}`,
    )
  },

  /** Returns the xlsx with diff cells highlighted (yellow/green/red) by the backend. */
  async getHighlighted(processId: string, versionId: string): Promise<Blob> {
    return api.blob(`/processes/${processId}/versions/${versionId}/highlighted`)
  },

  /**
   * Returns compact sheet JSON from the backend xlsx_parser.
   * Shape: { sheets: SheetData[] }  — see XlsxViewer.vue for the full type.
   */
  async getSheetData(processId: string, versionId: string): Promise<unknown> {
    return api.get(`/processes/${processId}/versions/${versionId}/sheet-data`)
  },

  /** Converts the version's xlsx to PDF via LibreOffice and returns the blob. */
  async getPdf(processId: string, versionId: string): Promise<Blob> {
    return api.blob(`/processes/${processId}/versions/${versionId}/highlighted-pdf`)
  },

  /** Follows the presigned download redirect and returns the raw xlsx blob. */
  async download(processId: string, versionId: string): Promise<Blob> {
    return api.blob(`/processes/${processId}/versions/${versionId}/download`)
  },

  /** Restores a version as active; all newer versions are soft-deleted. */
  async restore(processId: string, versionId: string): Promise<ApiProcessVersion> {
    return api.post<ApiProcessVersion>(`/processes/${processId}/versions/${versionId}/restore`, {})
  },
}