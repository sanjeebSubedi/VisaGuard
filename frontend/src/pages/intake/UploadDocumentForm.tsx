type UploadDocumentFormProps = {
  label: string
  helpText: string
}

export function UploadDocumentForm({ label, helpText }: UploadDocumentFormProps) {
  const inputId = label.toLowerCase().replace(/[^a-z0-9]+/g, '-')

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-900">
        {label}
      </label>
      <p className="mt-1 text-sm text-slate-600">{helpText}</p>
      <input id={inputId} type="file" className="mt-4 block w-full text-sm text-slate-700" />
    </section>
  )
}
