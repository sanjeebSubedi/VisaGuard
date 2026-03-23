import type { WorkflowRunResponse } from '@/api/types'
import { ActionCenter } from '@/pages/dashboard/ActionCenter'
import { ComplianceClockList } from '@/pages/dashboard/ComplianceClockList'
import { DocumentSummaryCard } from '@/pages/dashboard/DocumentSummaryCard'
import { DashboardEmptyState } from '@/pages/dashboard/empty-state'
import { HeroStatusCard } from '@/pages/dashboard/HeroStatusCard'
import { WorkflowRunControl } from '@/pages/dashboard/WorkflowRunControl'

type DashboardPageProps = {
  workflowResult?: WorkflowRunResponse
  isRunningWorkflow?: boolean
}

export function DashboardPage({ workflowResult, isRunningWorkflow = false }: DashboardPageProps) {
  const finalRecord = workflowResult?.final_compliance_record
  const clocks = (workflowResult?.timeline_status?.clocks as Record<string, {
    status: string
    limit_days?: number | null
    days_remaining?: number | null
    relevant_dates: Record<string, string>
  }> | undefined) ?? {}

  if (!finalRecord) {
    return (
      <div className="space-y-6">
        <WorkflowRunControl isRunning={isRunningWorkflow} />
        <DashboardEmptyState />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <WorkflowRunControl isRunning={isRunningWorkflow} />
      <HeroStatusCard record={finalRecord} />
      <ActionCenter actions={finalRecord.action_plan ?? []} />
      <ComplianceClockList clocks={clocks} />
      <DocumentSummaryCard />
    </div>
  )
}
