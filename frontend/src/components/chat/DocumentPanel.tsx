import { useDocuments } from "@/hooks/useDocuments"
import { FileUpload } from "@/components/common/FileUpload"

export function DocumentPanel() {
  const { documents, isUploading, uploadDocument, deleteDocument } = useDocuments()

  return (
    <div className="w-72 border-l border-gray-200 bg-white p-4 hidden xl:flex flex-col">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Documentos</h3>

      <FileUpload onUpload={uploadDocument} uploading={isUploading} />

      <div className="mt-4 space-y-2 flex-1 overflow-y-auto">
        {documents.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            No hay documentos cargados
          </p>
        )}
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-2 rounded-lg bg-gray-50 border border-gray-100"
          >
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-gray-700 truncate">
                {doc.filename}
              </p>
              <p className="text-xs text-gray-400">
                {doc.status === "ready"
                  ? `${doc.chunks} chunks`
                  : doc.status === "processing"
                    ? "Procesando..."
                    : "Error"}
              </p>
            </div>
            <button
              onClick={() => deleteDocument(doc.id)}
              className="text-gray-400 hover:text-red-500 ml-2 shrink-0"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
