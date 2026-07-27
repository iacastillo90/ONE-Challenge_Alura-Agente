import api, { getAccessToken, setAccessToken } from "@/services/api"

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

/**
 * Devuelve un token de acceso válido, renovándolo mediante la cookie httpOnly
 * cuando el token en memoria no existe o está por expirar. SSE utiliza fetch()
 * por lo que no depende del interceptor de respuestas de axios — replicamos esa
 * lógica aquí contra el mismo endpoint de actualización basado en cookies.
 */
async function getValidToken(): Promise<string | null> {
  const token = getAccessToken()

  if (token) {
    const payload = token.split(".")[1]
    if (payload) {
      try {
        const exp = JSON.parse(atob(payload)).exp
        const now = Math.floor(Date.now() / 1000)
        if (exp > now + 60) return token
      } catch {
        return token
      }
    } else {
      return token
    }
  }

  // Si no está disponible o está por expirar: actualizar mediante la cookie httpOnly.
  try {
    const res = await api.post<{ access_token: string }>(
      "/auth/refresh",
      {},
      { withCredentials: true },
    )
    setAccessToken(res.data.access_token)
    return res.data.access_token
  } catch {
    setAccessToken(null)
    return null
  }
}

function redirectToLogin() {
  if (window.location.pathname !== "/login") {
    window.location.href = "/login"
  }
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onToken: (token: string) => void,
  onDone: (full: string, sources: unknown[]) => void,
  onError: (code: string, msg: string) => void,
): Promise<void> {
  const token = await getValidToken()
  if (!token) {
    onError("AUTH_ERROR", "No autenticado")
    redirectToLogin()
    return
  }

  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    credentials: "include",
    body: JSON.stringify({ message, session_id: sessionId }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Error desconocido" }))
    if (response.status === 401) {
      setAccessToken(null)
      redirectToLogin()
    }
    onError("HTTP_ERROR", err.detail || `Estado ${response.status}`)
    return
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() || ""

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.code) {
            onError(data.code, data.message || "Error desconocido")
          } else if (data.done) {
            onDone(data.full_response || "", data.sources || [])
          } else {
            onToken(data.token || "")
          }
        } catch {
          // omitir líneas mal formateadas
        }
      }
    }
  }
}

export function createSessionId(): string {
  return crypto.randomUUID()
}
