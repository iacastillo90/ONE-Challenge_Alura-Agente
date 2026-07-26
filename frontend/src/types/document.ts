export type DocumentStatus = "processing" | "ready" | "error"

export interface Document {
  id: string
  filename: string
  status: DocumentStatus
  chunks: number
  created_at: string
  error?: string
}
