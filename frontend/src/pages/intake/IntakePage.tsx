import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '@/api/client'
import { createManualEadEntry, uploadDocument } from '@/api/intake'
import { queryKeys } from '@/api/queries'
import { ManualEADForm, type ManualEadValues } from '@/pages/intake/ManualEADForm'
import { UploadDocumentForm } from '@/pages/intake/UploadDocumentForm'
import { useUserId } from '@/state/use-user-id'

type IntakePageProps = {
  uploadMessage?: string
  eadMessage?: string
  errorMessage?: string
  onUploadI20?: (file: File) => void
  onUploadOfferLetter?: (file: File) => void
  onSaveManualEad?: (values: ManualEadValues) => void
  isUploading?: boolean
  isSavingManualEad?: boolean
}

export function IntakePage({
  uploadMessage,
  eadMessage,
  errorMessage,
  onUploadI20,
  onUploadOfferLetter,
  onSaveManualEad,
  isUploading = false,
  isSavingManualEad = false,
}: IntakePageProps) {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-800 bg-slate-900/95 p-8 shadow-xl shadow-slate-950/30">
        <h1 className="text-2xl font-semibold text-slate-50">Document intake</h1>
        <p className="mt-2 text-sm text-slate-400">
          Upload your I-20 and offer letter, or enter your EAD details manually.
        </p>
      </section>

      {uploadMessage ? <p className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{uploadMessage}</p> : null}
      {eadMessage ? <p className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{eadMessage}</p> : null}
      {errorMessage ? <p className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{errorMessage}</p> : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <UploadDocumentForm
          label="I-20 PDF"
          helpText="Upload the latest I-20 PDF issued by your school."
          accept="application/pdf"
          submitLabel="Upload I-20"
          onSubmit={onUploadI20}
          isSubmitting={isUploading}
        />
        <UploadDocumentForm
          label="Offer Letter PDF"
          helpText="Upload your signed job offer letter as a PDF."
          accept="application/pdf"
          submitLabel="Upload Offer Letter"
          onSubmit={onUploadOfferLetter}
          isSubmitting={isUploading}
        />
      </div>

      <ManualEADForm onSubmit={onSaveManualEad} isSubmitting={isSavingManualEad} />
    </div>
  )
}

export function IntakeRoute() {
  const { userId } = useUserId()
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: ({ documentType, file }: { documentType: 'i20' | 'offer_letter'; file: File }) =>
      uploadDocument({ userId, documentType, file }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(userId) })
      queryClient.removeQueries({ queryKey: queryKeys.workflowResult(userId) })
    },
  })

  const manualEadMutation = useMutation({
    mutationFn: (values: ManualEadValues) =>
      createManualEadEntry({
        userId,
        alienRegistrationNumber: values.alienRegistrationNumber,
        category: values.category,
        cardStartDate: values.cardStartDate,
        cardEndDate: values.cardEndDate,
        cardNumber: values.cardNumber,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.snapshot(userId) })
      queryClient.removeQueries({ queryKey: queryKeys.workflowResult(userId) })
    },
  })

  const errorMessage =
    uploadMutation.error instanceof ApiError
      ? uploadMutation.error.message
      : manualEadMutation.error instanceof ApiError
        ? manualEadMutation.error.message
        : undefined

  return (
    <IntakePage
      uploadMessage={uploadMutation.isSuccess ? 'Document uploaded successfully' : undefined}
      eadMessage={manualEadMutation.isSuccess ? 'Manual EAD saved' : undefined}
      errorMessage={errorMessage}
      onUploadI20={(file) => uploadMutation.mutate({ documentType: 'i20', file })}
      onUploadOfferLetter={(file) => uploadMutation.mutate({ documentType: 'offer_letter', file })}
      onSaveManualEad={(values) => manualEadMutation.mutate(values)}
      isUploading={uploadMutation.isPending}
      isSavingManualEad={manualEadMutation.isPending}
    />
  )
}
