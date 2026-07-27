import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/store/authStore"
import { Button } from "@/components/common/Button"
import { Input } from "@/components/common/Input"

type Mode = "login" | "register"

// Credenciales de prueba públicas (modificables mediante variables de entorno en tiempo de compilación).
// La cuenta se crea/siembra en la base de datos desde el backend, no está codificada de forma fija.
const DEMO_USER = import.meta.env.VITE_DEMO_USERNAME || "test@gmail.com"
const DEMO_PASS = import.meta.env.VITE_DEMO_PASSWORD || "1234567890"

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const register = useAuthStore((s) => s.register)
  const [mode, setMode] = useState<Mode>("login")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return
    if (mode === "register" && password !== confirm) {
      setError("Las contraseñas no coinciden")
      return
    }
    setLoading(true)
    setError("")
    const fn = mode === "login" ? login : register
    const result = await fn(username.trim(), password)
    setLoading(false)
    if (result.success) {
      navigate("/", { replace: true })
    } else {
      setError(result.error || (mode === "login" ? "Error al iniciar sesión" : "Error al registrarse"))
    }
  }

  const toggleMode = () => {
    setMode(mode === "login" ? "register" : "login")
    setError("")
  }

  const isLogin = mode === "login"

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8 shadow-2xl">
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 bg-indigo-600 rounded-xl flex items-center justify-center mb-4 shadow-lg shadow-indigo-600/20">
              <span className="text-xl text-white font-bold">AI</span>
            </div>
            <h1 className="text-xl font-bold text-white">ONE AI Agent</h1>
            <p className="text-sm text-gray-400 mt-1">
              {isLogin ? "Inicia sesión para continuar" : "Crea una cuenta nueva"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Usuario"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Tu nombre de usuario"
              className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-indigo-500"
            />
            <Input
              label="Contraseña"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-indigo-500"
            />
            {!isLogin && (
              <Input
                label="Confirmar contraseña"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 focus:border-indigo-500"
              />
            )}

            {error && (
              <p className="text-sm text-red-400 bg-red-950/50 border border-red-900/50 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full">
              {loading
                ? isLogin
                  ? "Iniciando sesión…"
                  : "Registrando…"
                : isLogin
                  ? "Iniciar Sesión"
                  : "Crear Cuenta"}
            </Button>
          </form>

          <p className="text-center mt-6">
            <button
              type="button"
              onClick={toggleMode}
              className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              {isLogin
                ? "¿No tenés cuenta? Registrate"
                : "¿Ya tenés cuenta? Iniciá sesión"}
            </button>
          </p>

          {isLogin && (
            <div className="mt-6 pt-4 border-t border-gray-800">
              <p className="text-[11px] text-gray-500 text-center leading-relaxed">
                Cuenta de prueba para demo
                <br />
                <button
                  type="button"
                  onClick={() => {
                    setUsername(DEMO_USER)
                    setPassword(DEMO_PASS)
                  }}
                  className="mt-1 inline-flex items-center gap-1 font-mono text-gray-400 hover:text-indigo-300 transition-colors"
                  title="Usar credenciales de prueba"
                >
                  {DEMO_USER} · {DEMO_PASS}
                </button>
              </p>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-gray-600 mt-6">
          Challenge ONE AI FOR TECH — Alura Latam
        </p>
      </div>
    </div>
  )
}
