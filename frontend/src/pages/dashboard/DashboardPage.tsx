import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '@/api/client'
import { getSnapshot } from '@/api/intake'
import { queryKeys } from '@/api/queries'
import type { SnapshotResponse, WorkflowResultResponse, WorkflowRunResponse } from '@/api/types'
import { getLatestWorkflowResult, runComplianceWorkflow } from '@/api/workflows'
import { ActionCenter } from '@/pages/dashboard/ActionCenter'
import { ComplianceClockList } from '@/pages/dashboard/ComplianceClockList'
import { DocumentSummaryCard } from '@/pages/dashboard/DocumentSummaryCard'
import { DashboardEmptyState } from '@/pages/dashboard/empty-state'
import { HeroStatusCard } from '@/pages/dashboard/HeroStatusCard'
import { WorkflowRunControl } from '@/pages/dashboard/WorkflowRunControl'
import { useUserId } from '@/state/use-user-id'

type DashboardPageProps = {
  workflowResult?: WorkflowResultResponse
  snapshot?: SnapshotResponse | null
  isRunningWorkflow?: boolean
  onRunWorkflow?: () => void
  errorMessage?: string
}

export function DashboardPage({
  workflowResult,
  snapshot,
  isRunningWorkflow = false,
  onRunWorkflow,
  errorMessage,
}: DashboardPageProps) {
  const finalRecord = workflowResult?.final_compliance_record
  const clocks = (workflowResult?.timeline_status?.clocks as Record<string, {
    status: string
    limit_days?: number | null
    days_remaining?: number | null
    relevant_dates: Record<string, string>
  }> | undefined) ?? {}

  return (
    <div className="space-y-6">
      <WorkflowRunControl isRunning={isRunningWorkflow} onRun={onRunWorkflow} />
      {errorMessage ? (
        <p className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{errorMessage}</p>
      ) : null}
      {!finalRecord ? <DashboardEmptyState /> : <HeroStatusCard record={finalRecord} />}
      {finalRecord ? <ActionCenter actions={finalRecord.action_plan ?? []} /> : null}
      {finalRecord ? <ComplianceClockList clocks={clocks} evaluationDate={workflowResult?.evaluation_date} /> : null}
      <DocumentSummaryCard snapshot={snapshot} workflowResult={workflowResult} />
    </div>
  )
}

async function getLatestWorkflowResultOrNull(userId: string) {
  try {
    return await getLatestWorkflowResult(userId)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null
    }
    throw error
  }
}

async function getSnapshotOrNull(userId: string) {
  try {
    return await getSnapshot(userId)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null
    }
    throw error
  }
}

export function DashboardRoute() {
  const { userId } = useUserId()
  const queryClient = useQueryClient()

  const workflowQuery = useQuery({
    queryKey: queryKeys.workflowResult(userId),
    queryFn: () => getLatestWorkflowResultOrNull(userId),
    retry: false,
  })

  const snapshotQuery = useQuery({
    queryKey: queryKeys.snapshot(userId),
    queryFn: () => getSnapshotOrNull(userId),
    retry: false,
  })

  const workflowMutation = useMutation({
    mutationFn: () => runComplianceWorkflow({ userId }),
    onSuccess: (result) => {
      queryClient.setQueryData<WorkflowResultResponse>(queryKeys.workflowResult(userId), {
        user_id: userId,
        evaluation_date: new Date().toISOString().slice(0, 10),
        timeline_status: result.timeline_status ?? {},
        policy_analysis: result.policy_analysis ?? {},
        policy_verdict: result.policy_verdict ?? {},
        final_compliance_record: result.final_compliance_record,
      })
    },
  })

  const errorMessage =
    workflowMutation.error instanceof ApiError
      ? workflowMutation.error.message
      : workflowQuery.error instanceof ApiError
        ? workflowQuery.error.message
        : snapshotQuery.error instanceof ApiError
          ? snapshotQuery.error.message
          : undefined

  return (
    <DashboardPage
      workflowResult={workflowQuery.data ?? undefined}
      snapshot={snapshotQuery.data ?? undefined}
      isRunningWorkflow={workflowMutation.isPending}
      onRunWorkflow={() => workflowMutation.mutate()}
      errorMessage={errorMessage}
    />
  )
}
