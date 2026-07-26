import { create } from "zustand"
import type { Document } from "@/types/document"
import { documentService } from "@/services/documentService"

interface DocumentStore {
  documents: Document[]
  isUploading: boolean
  fetchDocuments: () => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  deleteDocument: (id: string) => Promise<void>
}

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  documents: [],
  isUploading: false,

  fetchDocuments: async () => {
    const docs = await documentService.list()
    set({ documents: docs })
  },

  uploadDocument: async (file) => {
    set({ isUploading: true })
    try {
      await documentService.upload(file)
      await get().fetchDocuments()
    } finally {
      set({ isUploading: false })
    }
  },

  deleteDocument: async (id) => {
    await documentService.delete(id)
    await get().fetchDocuments()
  },
}))
