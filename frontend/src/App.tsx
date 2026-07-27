import { useEffect } from "react"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppLayout } from "@/components/layout/AppLayout"
import { ProtectedRoute } from "@/components/common/ProtectedRoute"
import { LoginPage } from "@/pages/LoginPage"
import { HomePage } from "@/pages/HomePage"
import { ChatPage } from "@/pages/ChatPage"
import { DocumentsPage } from "@/pages/DocumentsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import { useAuthStore } from "@/store/authStore"

const queryClient = new QueryClient()

function App() {
  const init = useAuthStore((s) => s.init)

  useEffect(() => { init() }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route
              path="/"
              element={<ProtectedRoute><HomePage /></ProtectedRoute>}
            />
            <Route
              path="/chat"
              element={<ProtectedRoute><ChatPage /></ProtectedRoute>}
            />
            <Route
              path="/documents"
              element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>}
            />
            <Route
              path="/settings"
              element={<ProtectedRoute><SettingsPage /></ProtectedRoute>}
            />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
