import { NavLink } from "react-router-dom"
import { useChatStore } from "@/store/chatStore"

const nav = [
  { to: "/chat", label: "Chat", icon: "💬" },
  { to: "/documents", label: "Documentos", icon: "📄" },
  { to: "/settings", label: "Configuración", icon: "⚙️" },
]

export function Sidebar() {
  const sessions = useChatStore((s) => s.sessions)
  const activeSession = useChatStore((s) => s.activeSession)
  const newSession = useChatStore((s) => s.newSession)

  return (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col shrink-0 hidden md:flex">
      <div className="p-4 border-b border-gray-100">
        <NavLink to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            AI
          </div>
          <span className="font-semibold text-gray-800">ONE Agent</span>
        </NavLink>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-indigo-50 text-indigo-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        <div className="pt-4 pb-2">
          <div className="flex items-center justify-between px-3">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Sesiones</span>
            <button onClick={newSession} className="text-xs text-indigo-600 hover:text-indigo-800">+ nueva</button>
          </div>
        </div>

        {Object.values(sessions).slice(-5).reverse().map((s) => (
          <button
            key={s.id}
            onClick={() => useChatStore.setState({ activeSession: s.id })}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors ${
              s.id === activeSession
                ? "bg-indigo-50 text-indigo-700"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            {s.messages.find((m) => m.role === "user")?.content.slice(0, 40) || "Nueva conversación"}
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-gray-100">
        <div className="text-xs text-gray-400">ONE AI FOR TECH</div>
      </div>
    </aside>
  )
}
