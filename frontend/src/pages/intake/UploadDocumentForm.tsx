import { useState } from 'react'

type UploadDocumentFormProps = {
  label: string
  helpText: string
  accept?: string
  onSubmit?: (file: File) => void
  submitLabel?: string
  isSubmitting?: boolean
}

export function UploadDocumentForm({
  label,
  helpText,
  accept,
  onSubmit,
  submitLabel = 'Upload document',
  isSubmitting = false,
}: UploadDocumentFormProps) {
  const inputId = label.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  return (
    <form
      className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        if (selectedFile && onSubmit) {
          onSubmit(selectedFile)
        }
      }}
    >
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-900">
        {label}
      </label>
      <p className="mt-1 text-sm text-slate-600">{helpText}</p>
      <input
        id={inputId}
        type="file"
        accept={accept}
        className="mt-4 block w-full text-sm text-slate-700"
        onChange={(event) => {
          setSelectedFile(event.currentTarget.files?.[0] ?? null)
        }}
      />
      <button
        type="submit"
        disabled={!selectedFile || isSubmitting}
        className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isSubmitting ? 'Uploading...' : submitLabel}
      </button>
    </form>
  )
}
