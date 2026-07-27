import { create } from "zustand"
import axios from "axios"
import api, { setAccessToken } from "@/services/api"
import type { LoginResponse } from "@/types/auth"
import { AUTH_KEYS } from "@/types/auth"

interface AuthStore {
  token: string | null
  userId: string | null
  username: string | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => Promise<void>
  init: () => Promise<void>
}

// El token de acceso se mantiene únicamente en memoria (ver services/api.ts). Se persisten
// solo pistas de identidad no sensibles para renderizar la UI de inmediato; la
// cookie de actualización httpOnly es la fuente de verdad entre recargas.
function persistIdentity(userId: string, username: string) {
  localStorage.setItem(AUTH_KEYS.userId, userId)
  localStorage.setItem(AUTH_KEYS.username, username)
}

function clearIdentity() {
  localStorage.removeItem(AUTH_KEYS.userId)
  localStorage.removeItem(AUTH_KEYS.username)
  localStorage.removeItem(AUTH_KEYS.token) // limpiar tokens persisentes heredados
  localStorage.removeItem(AUTH_KEYS.refreshToken)
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  userId: null,
  username: null,
  isAuthenticated: false,
  isInitializing: true,

  init: async () => {
    // Regenerar token de acceso mediante la cookie httpOnly de actualización, si está presente.
    try {
      const res = await api.post<{ access_token: string; user_id: string; username: string }>(
        "/auth/refresh",
        {},
        { withCredentials: true },
      )
      const t = res.data.access_token
      setAccessToken(t)
      persistIdentity(res.data.user_id, res.data.username)
      set({
        token: t,
        userId: res.data.user_id,
        username: res.data.username,
        isAuthenticated: true,
      })
    } catch {
      clearIdentity()
      set({ token: null, userId: null, username: null, isAuthenticated: false })
    } finally {
      set({ isInitializing: false })
    }
  },

  login: async (username: string, password: string) => {
    try {
      const res = await api.post<LoginResponse>(
        "/auth/login",
        { username, password },
        { withCredentials: true },
      )
      const { access_token: token, user_id: userId, username: uname } = res.data
      if (res.data.requires_2fa || !token) {
        return { success: false, error: "Se requiere código 2FA para esta cuenta" }
      }
      setAccessToken(token)
      persistIdentity(userId, uname)
      set({ token, userId, username: uname, isAuthenticated: true })
      return { success: true }
    } catch (err) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Error al iniciar sesión"
      return { success: false, error: msg }
    }
  },

  register: async (username: string, password: string) => {
    try {
      const res = await api.post<LoginResponse>(
        "/auth/register",
        { username, password },
        { withCredentials: true },
      )
      const { access_token: token, user_id: userId, username: uname } = res.data
      setAccessToken(token)
      persistIdentity(userId, uname)
      set({ token, userId, username: uname, isAuthenticated: true })
      return { success: true }
    } catch (err) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Error al registrarse"
      return { success: false, error: msg }
    }
  },

  logout: async () => {
    try {
      await api.post("/auth/logout")
    } catch {
      // ignorar errores del servidor durante el cierre de sesión
    }
    setAccessToken(null)
    clearIdentity()
    set({ token: null, userId: null, username: null, isAuthenticated: false })
  },
}))
