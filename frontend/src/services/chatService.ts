const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onToken: (token: string) => void,
  onDone: (full: string, sources: unknown[]) => void,
  onError: (code: string, msg: string) => void,
): Promise<void> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Unknown error" }))
    onError("HTTP_ERROR", err.detail || `Status ${response.status}`)
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
            onError(data.code, data.message || "Unknown error")
          } else if (data.done) {
            onDone(data.full_response || "", data.sources || [])
          } else {
            onToken(data.token || "")
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}

export function createSessionId(): string {
  return crypto.randomUUID()
}
