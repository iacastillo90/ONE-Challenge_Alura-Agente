import { useEffect } from "react"
import { useDocumentStore } from "@/store/documentStore"

export function useDocuments() {
  const store = useDocumentStore()

  useEffect(() => {
    store.fetchDocuments()
  }, [])

  return store
}
