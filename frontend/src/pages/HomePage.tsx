import { Link } from "react-router-dom"
import { Button } from "@/components/common/Button"

export function HomePage() {
  return (
    <div className="min-h-full flex items-center justify-center p-8">
      <div className="text-center max-w-2xl">
        <div className="w-20 h-20 bg-indigo-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-lg">
          <span className="text-3xl text-white font-bold">AI</span>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          ONE AI Agent
        </h1>
        <p className="text-lg text-gray-600 mb-2">
          Challenge ONE AI FOR TECH — Alura Latam
        </p>
        <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto">
          Agente inteligente con RAG que responde preguntas basadas en tus documentos PDF y CSV.
          Soporta múltiples proveedores LLM con failover automático.
        </p>

        <div className="flex gap-4 justify-center">
          <Link to="/chat">
            <Button>Ir al Chat</Button>
          </Link>
          <Link to="/documents">
            <Button variant="secondary">Subir Documentos</Button>
          </Link>
        </div>

        <div className="mt-12 grid grid-cols-3 gap-6 text-left">
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-2xl mb-2">📄</div>
            <h3 className="text-sm font-semibold text-gray-800">RAG</h3>
            <p className="text-xs text-gray-500 mt-1">Búsqueda semántica en PDFs y CSVs</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-2xl mb-2">🔄</div>
            <h3 className="text-sm font-semibold text-gray-800">Multi-Provider</h3>
            <p className="text-xs text-gray-500 mt-1">Gemini, Groq, DeepSeek con failover</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200">
            <div className="text-2xl mb-2">🧠</div>
            <h3 className="text-sm font-semibold text-gray-800">Memoria</h3>
            <p className="text-xs text-gray-500 mt-1">Contexto conversacional persistente</p>
          </div>
        </div>
      </div>
    </div>
  )
}
