import { apiRequest } from '@/api/client'
import type { DocumentResponse, ManualEadEntryInput, UploadDocumentInput } from '@/api/types'

export function uploadDocument(input: UploadDocumentInput) {
  const formData = new FormData()
  formData.append('user_id', input.userId)
  formData.append('document_type', input.documentType)
  formData.append('file', input.file)

  return apiRequest<DocumentResponse>('/api/intake/documents', {
    method: 'POST',
    body: formData,
  })
}

export function createManualEadEntry(input: ManualEadEntryInput) {
  return apiRequest<DocumentResponse>('/api/intake/ead/manual', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: input.userId,
      alien_registration_number: input.alienRegistrationNumber,
      category: input.category,
      card_start_date: input.cardStartDate,
      card_end_date: input.cardEndDate,
      card_number: input.cardNumber,
    }),
  })
}
