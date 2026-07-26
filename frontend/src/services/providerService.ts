import api from "./api"
import type { Provider } from "@/types/provider"

export const providerService = {
  async list(): Promise<Provider[]> {
    const { data } = await api.get("/providers")
    return data.providers
  },

  async switch(provider: string | null): Promise<void> {
    await api.post("/providers/switch", { provider })
  },

  async getActive(): Promise<string | null> {
    const { data } = await api.get("/providers")
    return data.active
  },
}
