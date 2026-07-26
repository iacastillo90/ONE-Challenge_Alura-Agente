export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: Source[]
  timestamp: string
}

export interface Source {
  document_name: string
  chunk: string
  score: number | null
}

export interface ChatSession {
  id: string
  messages: Message[]
  created_at: string
}
