import { useProviders } from "@/hooks/useProviders"
import { Button } from "@/components/common/Button"

export function SettingsPage() {
  const { providers, activeProvider, switchProvider } = useProviders()

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Configuración</h1>

      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Proveedores LLM
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          El sistema usa failover automático: si el proveedor activo falla, rota al siguiente.
          {activeProvider && (
            <span className="block mt-1 text-indigo-600 font-medium">
              Activo ahora: <code className="bg-indigo-50 px-2 py-0.5 rounded">{activeProvider}</code>
            </span>
          )}
        </p>

        <div className="space-y-3">
          {providers.map((p) => (
            <div
              key={p.name}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                p.name === activeProvider
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-gray-200"
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">{p.name}</span>
                  <span className={`w-2 h-2 rounded-full ${
                    p.available ? "bg-green-500" : "bg-red-400"
                  }`} />
                  <span className="text-xs text-gray-400">
                    Prioridad {p.priority}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">Modelo: {p.model || "—"}</p>
                {p.degraded && (
                  <p className="text-xs text-yellow-600 mt-0.5">⚠ Degradado temporalmente</p>
                )}
              </div>
              <Button
                variant={p.name === activeProvider ? "primary" : "secondary"}
                size="small"
                onClick={() => switchProvider(p.name === activeProvider ? null : p.name)}
              >
                {p.name === activeProvider ? "Activo" : "Usar"}
              </Button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 mt-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">
          Acerca del Proyecto
        </h2>
        <p className="text-sm text-gray-500">
          Challenge ONE AI FOR TECH — Alura Latam. Agente inteligente con RAG,
          soporte multi-provider LLM, embeddings locales (sentence-transformers),
          ChromaDB vector store y orquestación vía n8n.
        </p>
      </section>
    </div>
  )
}
