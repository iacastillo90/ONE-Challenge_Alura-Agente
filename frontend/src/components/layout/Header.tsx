import { Link } from "react-router-dom"

export function Header() {
  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 shrink-0">
      <Link to="/" className="text-lg font-bold text-indigo-700">
        ONE AI Agent
      </Link>
      <span className="ml-3 text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Alura Challenge</span>
      <div className="ml-auto flex items-center gap-4 text-sm text-gray-500">
        <span className="hidden sm:inline">Agente inteligente con RAG</span>
      </div>
    </header>
  )
}
