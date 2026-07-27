import { Navigate } from "react-router-dom"
import { useAuthStore } from "@/store/authStore"
import { Spinner } from "./Spinner"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const token = useAuthStore((s) => s.token)
  const isInitializing = useAuthStore((s) => s.isInitializing)

  if (isInitializing) {
    return <Spinner />
  }

  if (!token || !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
