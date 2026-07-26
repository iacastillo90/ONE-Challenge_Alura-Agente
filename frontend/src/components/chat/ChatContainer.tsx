import { useEffect, useRef } from "react"
import { useChatStore } from "@/store/chatStore"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { DocumentPanel } from "./DocumentPanel"

export function ChatContainer() {
  const session = useChatStore((s) =>
    s.activeSession ? s.sessions[s.activeSession] : null,
  )
  const isStreaming = useChatStore((s) => s.isStreaming)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [session?.messages])

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!session || session.messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🤖</span>
                </div>
                <h2 className="text-xl font-semibold text-gray-800 mb-2">
                  ONE AI Agent
                </h2>
                <p className="text-sm text-gray-500">
                  Subí documentos PDF o CSV y hace preguntas sobre su contenido.
                  El agente busca la información relevante y te responde citando las fuentes.
                </p>
              </div>
            </div>
          ) : (
            session.messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
          <div ref={bottomRef} />
        </div>

        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </div>

      <DocumentPanel />
    </div>
  )
}
