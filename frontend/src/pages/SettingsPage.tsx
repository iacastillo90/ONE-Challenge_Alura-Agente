import { useState } from "react"
import { useProviders } from "@/hooks/useProviders"
import { Button } from "@/components/common/Button"
import { Input } from "@/components/common/Input"
import { sendWhatsApp } from "@/services/whatsappService"

export function SettingsPage() {
  const { providers, activeProvider, switchProvider } = useProviders()

  const [waNumber, setWaNumber] = useState("")
  const [waMessage, setWaMessage] = useState("")
  const [waStatus, setWaStatus] = useState<{ ok: boolean; text: string } | null>(null)
  const [waSending, setWaSending] = useState(false)

  const handleSendWhatsApp = async () => {
    if (!waMessage.trim()) return
    setWaSending(true)
    setWaStatus(null)
    try {
      const res = await sendWhatsApp(waMessage.trim(), waNumber.trim() || undefined)
      setWaStatus({ ok: true, text: `Mensaje enviado a ${res.to}` })
      setWaMessage("")
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "No se pudo enviar el mensaje"
      setWaStatus({ ok: false, text: detail })
    } finally {
      setWaSending(false)
    }
  }

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
        <h2 className="text-lg font-semibold text-gray-800 mb-2">WhatsApp</h2>
        <p className="text-sm text-gray-500 mb-4">
          Enviá un mensaje a un número de WhatsApp a través de la orquestación n8n.
          Si dejás el número vacío se usa el número por defecto de la plataforma.
        </p>
        <div className="space-y-3">
          <Input
            label="Número destino (E.164, opcional)"
            type="tel"
            value={waNumber}
            onChange={(e) => setWaNumber(e.target.value)}
            placeholder="+5491122334455"
          />
          <Input
            label="Mensaje"
            type="text"
            value={waMessage}
            onChange={(e) => setWaMessage(e.target.value)}
            placeholder="Hola desde ONE AI Agent"
          />
          {waStatus && (
            <p className={`text-sm ${waStatus.ok ? "text-green-600" : "text-red-500"}`}>
              {waStatus.text}
            </p>
          )}
          <Button onClick={handleSendWhatsApp} loading={waSending} disabled={!waMessage.trim()}>
            Enviar por WhatsApp
          </Button>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 mt-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">
          Acerca del Proyecto
        </h2>
        <p className="text-sm text-gray-500">
          Challenge ONE AI FOR TECH — Alura Latam. Agente inteligente con RAG,
          soporte multi-provider LLM, embeddings locales (sentence-transformers),
          vector store en PostgreSQL + pgvector, almacenamiento de archivos en
          MinIO y orquestación vía n8n (incluye canal WhatsApp).
        </p>
      </section>
    </div>
  )
}
