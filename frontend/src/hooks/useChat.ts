import { useEffect } from "react"
import { useChatStore } from "@/store/chatStore"

export function useChat() {
  const store = useChatStore()

  useEffect(() => {
    if (!store.activeSession) {
      store.newSession()
    }
  }, [])

  return store
}
