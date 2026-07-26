import { useDocuments } from "@/hooks/useDocuments"
import { FileUpload } from "@/components/common/FileUpload"

export function DocumentsPage() {
  const { documents, isUploading, uploadDocument, deleteDocument } = useDocuments()

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Documentos</h1>

      <FileUpload onUpload={uploadDocument} uploading={isUploading} />

      <div className="mt-8 space-y-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          Documentos cargados ({documents.length})
        </h2>

        {documents.length === 0 && (
          <p className="text-sm text-gray-400">No hay documentos cargados</p>
        )}

        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200"
          >
            <div>
              <p className="text-sm font-medium text-gray-800">{doc.filename}</p>
              <div className="flex gap-3 mt-1">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  doc.status === "ready"
                    ? "bg-green-100 text-green-700"
                    : doc.status === "processing"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-red-100 text-red-700"
                }`}>
                  {doc.status === "ready" ? "Listo" : doc.status === "processing" ? "Procesando" : "Error"}
                </span>
                {doc.status === "ready" && (
                  <span className="text-xs text-gray-400">{doc.chunks} chunks indexados</span>
                )}
              </div>
              {doc.error && <p className="text-xs text-red-500 mt-1">{doc.error}</p>}
            </div>
            <button
              onClick={() => deleteDocument(doc.id)}
              className="text-gray-400 hover:text-red-500"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
