import { useCallback, useRef, type DragEvent } from "react"

interface FileUploadProps {
  onUpload: (file: File) => void
  uploading?: boolean
  accept?: string
}

export function FileUpload({ onUpload, uploading, accept = ".pdf,.csv" }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file) onUpload(file)
    },
    [onUpload],
  )

  const handleChange = () => {
    const file = inputRef.current?.files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors cursor-pointer"
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
      />
      <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
      <p className="mt-2 text-sm text-gray-600">
        {uploading ? "Subiendo..." : "Arrastra un archivo o haz clic para subir"}
      </p>
      <p className="text-xs text-gray-400 mt-1">PDF o CSV</p>
    </div>
  )
}
