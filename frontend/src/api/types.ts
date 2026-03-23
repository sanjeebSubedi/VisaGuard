export type DocumentType = 'i20' | 'ead' | 'offer_letter'

export type DocumentResponse = {
  id?: number
  user_id?: string
  document_type: DocumentType
  parse_status?: string
  redaction_status?: string
  extraction_status?: string
}

export type ManualEadEntryInput = {
  userId: string
  alienRegistrationNumber: string
  category: string
  cardStartDate: string
  cardEndDate: string
  cardNumber?: string
}

export type UploadDocumentInput = {
  userId: string
  documentType: Exclude<DocumentType, 'ead'> | 'ead'
  file: File
}

export type WorkflowRunInput = {
  userId: string
  evaluationDate?: string
}

export type WorkflowRunResponse = {
  final_compliance_record?: {
    overall_state: string
    severity?: string
    action_plan?: string[]
    audit_summary?: string
  }
  timeline_status?: Record<string, unknown>
  policy_verdict?: Record<string, unknown>
  policy_analysis?: Record<string, unknown>
}

export type WorkflowResultResponse = WorkflowRunResponse & {
  user_id: string
  evaluation_date: string
}

export type SnapshotResponse = {
  user_id: string
  version: number
  snapshot_payload: Record<string, unknown>
  field_eligibility_map: Record<string, unknown>
  provenance_map: Record<string, unknown>
}
