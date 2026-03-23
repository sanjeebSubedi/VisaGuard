import { apiRequest } from '@/api/client'
import type { WorkflowRunInput, WorkflowRunResponse } from '@/api/types'

export const WORKFLOW_RUN_TIMEOUT_MS = 30000

export function runComplianceWorkflow(input: WorkflowRunInput) {
  return apiRequest<WorkflowRunResponse>('/api/workflows/compliance/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: input.userId,
      evaluation_date: input.evaluationDate,
    }),
    timeoutMs: WORKFLOW_RUN_TIMEOUT_MS,
  })
}
