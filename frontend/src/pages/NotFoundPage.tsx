import { Link } from "react-router-dom"

export function NotFoundPage() {
  return (
    <div className="min-h-full flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-200">404</h1>
        <p className="text-lg text-gray-600 mt-2">Página no encontrada</p>
        <Link to="/" className="text-indigo-600 hover:text-indigo-800 text-sm mt-4 inline-block">
          Volver al inicio
        </Link>
      </div>
    </div>
  )
}
