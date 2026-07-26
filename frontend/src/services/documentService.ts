import api from "./api"
import type { Document } from "@/types/document"

export const documentService = {
  async upload(file: File): Promise<Document> {
    const form = new FormData()
    form.append("file", file)
    const { data } = await api.post("/documents/upload", form)
    return data
  },

  async list(): Promise<Document[]> {
    const { data } = await api.get("/documents")
    return data.documents
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/documents/${id}`)
  },
}
