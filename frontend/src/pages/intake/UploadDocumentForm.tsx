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
      className="rounded-3xl border border-slate-800 bg-slate-900/95 p-6 shadow-xl shadow-slate-950/30"
      onSubmit={(event) => {
        event.preventDefault()
        if (selectedFile && onSubmit) {
          onSubmit(selectedFile)
        }
      }}
    >
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-100">
        {label}
      </label>
      <p className="mt-1 text-sm text-slate-400">{helpText}</p>
      <input
        id={inputId}
        type="file"
        accept={accept}
        className="mt-4 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-800 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-200"
        onChange={(event) => {
          setSelectedFile(event.currentTarget.files?.[0] ?? null)
        }}
      />
      <button
        type="submit"
        disabled={!selectedFile || isSubmitting}
        className="mt-4 rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {isSubmitting ? 'Uploading...' : submitLabel}
      </button>
    </form>
  )
}
