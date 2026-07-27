import { useEffect } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuthStore } from "@/store/authStore"

export function Header() {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const username = useAuthStore((s) => s.username)
  const logout = useAuthStore((s) => s.logout)
  const init = useAuthStore((s) => s.init)

  useEffect(() => { init() }, [])

  const handleLogout = () => {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 shrink-0">
      <Link to="/" className="text-lg font-bold text-indigo-700">
        ONE AI Agent
      </Link>
      <span className="ml-3 text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Alura Challenge</span>
      <div className="ml-auto flex items-center gap-4 text-sm text-gray-500">
        {token && username && (
          <>
            <span className="hidden sm:inline text-gray-700 font-medium">{username}</span>
            <button
              onClick={handleLogout}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              Cerrar sesión
            </button>
          </>
        )}
        {!token && <span className="hidden sm:inline">Agente inteligente con RAG</span>}
      </div>
    </header>
  )
}
