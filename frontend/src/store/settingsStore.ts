import { create } from "zustand"
import type { Provider } from "@/types/provider"
import { providerService } from "@/services/providerService"

interface SettingsStore {
  providers: Provider[]
  activeProvider: string | null
  fetchProviders: () => Promise<void>
  switchProvider: (name: string | null) => Promise<void>
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  providers: [],
  activeProvider: null,

  fetchProviders: async () => {
    const providers = await providerService.list()
    const active = await providerService.getActive()
    set({ providers, activeProvider: active })
  },

  switchProvider: async (name) => {
    await providerService.switch(name)
    set({ activeProvider: name })
    await get().fetchProviders()
  },
}))
