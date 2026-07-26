import { useEffect, useState } from "react"

interface ToastProps {
  message: string
  type?: "success" | "error" | "info"
  onClose: () => void
  duration?: number
}

export function Toast({ message, type = "info", onClose, duration = 4000 }: ToastProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false)
      setTimeout(onClose, 300)
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  const colors = {
    success: "bg-green-50 border-green-200 text-green-800",
    error: "bg-red-50 border-red-200 text-red-800",
    info: "bg-indigo-50 border-indigo-200 text-indigo-800",
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 border rounded-lg px-4 py-3 shadow-lg transition-opacity duration-300 ${colors[type]} ${visible ? "opacity-100" : "opacity-0"}`}
    >
      <div className="flex items-center gap-3">
        <span className="text-sm">{message}</span>
        <button onClick={() => { setVisible(false); setTimeout(onClose, 300) }} className="text-current opacity-60 hover:opacity-100">&times;</button>
      </div>
    </div>
  )
}
