import { create } from "zustand"
import type { Message, ChatSession } from "@/types/chat"
import { sendChatMessage, createSessionId } from "@/services/chatService"

interface ChatStore {
  sessions: Record<string, ChatSession>
  activeSession: string | null
  isStreaming: boolean

  sendMessage: (content: string) => Promise<void>
  addToken: (sessionId: string, token: string) => void
  finalizeMessage: (sessionId: string, full: string, sources: unknown[]) => void
  newSession: () => string
  clearSession: (sessionId: string) => void
  setStreaming: (v: boolean) => void
  setError: (sessionId: string, code: string, msg: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: {},
  activeSession: null,
  isStreaming: false,

  setStreaming: (v) => set({ isStreaming: v }),

  newSession: () => {
    const id = createSessionId()
    set((s) => ({
      activeSession: id,
      sessions: {
        ...s.sessions,
        [id]: { id, messages: [], created_at: new Date().toISOString() },
      },
    }))
    return id
  },

  sendMessage: async (content: string) => {
    let sessionId = get().activeSession
    if (!sessionId) {
      sessionId = get().newSession()
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    }

    set((s) => ({
      isStreaming: true,
      sessions: {
        ...s.sessions,
        [sessionId!]: {
          ...s.sessions[sessionId!],
          messages: [...(s.sessions[sessionId!]?.messages || []), userMsg],
        },
      },
    }))

    const assistantId = crypto.randomUUID()
    const partial: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    }

    set((s) => ({
      sessions: {
        ...s.sessions,
        [sessionId!]: {
          ...s.sessions[sessionId!],
          messages: [...(s.sessions[sessionId!]?.messages || []), partial],
        },
      },
    }))

    await sendChatMessage(
      content,
      sessionId,
      (token) => get().addToken(sessionId, token),
      (full, sources) => get().finalizeMessage(sessionId, full, sources),
        (_code, msg) => get().setError(sessionId, _code, msg),
    )
  },

  addToken: (sessionId, token) => {
    set((s) => {
      const session = s.sessions[sessionId]
      if (!session) return s
      const messages = [...session.messages]
      const last = messages[messages.length - 1]
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + token }
      }
      return {
        sessions: { ...s.sessions, [sessionId]: { ...session, messages } },
      }
    })
  },

  finalizeMessage: (sessionId, full, sources) => {
    set((s) => {
      const session = s.sessions[sessionId]
      if (!session) return s
      const messages = [...session.messages]
      const last = messages[messages.length - 1]
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: full, sources: sources as any }
      }
      return {
        isStreaming: false,
        sessions: { ...s.sessions, [sessionId]: { ...session, messages } },
      }
    })
  },

  setError: (sessionId, _code, msg) => {
    set((s) => {
      const session = s.sessions[sessionId]
      if (!session) return s
      const messages = [...session.messages]
      const last = messages[messages.length - 1]
      if (last?.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          content: `⚠️ Error: ${msg}`,
        }
      }
      return {
        isStreaming: false,
        sessions: { ...s.sessions, [sessionId]: { ...session, messages } },
      }
    })
  },

  clearSession: (sessionId) => {
    set((s) => {
      const { [sessionId]: _, ...rest } = s.sessions
      const next = Object.keys(rest)[0] || null
      return { sessions: rest, activeSession: next }
    })
  },
}))
