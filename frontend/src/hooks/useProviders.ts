import { useEffect } from "react"
import { useSettingsStore } from "@/store/settingsStore"

export function useProviders() {
  const store = useSettingsStore()

  useEffect(() => {
    store.fetchProviders()
  }, [])

  return store
}
