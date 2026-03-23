import { ManualEADForm } from '@/pages/intake/ManualEADForm'
import { UploadDocumentForm } from '@/pages/intake/UploadDocumentForm'

type IntakePageProps = {
  uploadMessage?: string
  eadMessage?: string
  errorMessage?: string
}

export function IntakePage({ uploadMessage, eadMessage, errorMessage }: IntakePageProps) {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Document intake</h1>
        <p className="mt-2 text-sm text-slate-600">
          Upload your I-20 and offer letter, or enter your EAD details manually.
        </p>
      </section>

      {uploadMessage ? <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{uploadMessage}</p> : null}
      {eadMessage ? <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{eadMessage}</p> : null}
      {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{errorMessage}</p> : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <UploadDocumentForm label="I-20 PDF" helpText="Upload the latest I-20 PDF issued by your school." />
        <UploadDocumentForm label="Offer Letter PDF" helpText="Upload your signed job offer letter as a PDF." />
      </div>

      <ManualEADForm />
    </div>
  )
}
