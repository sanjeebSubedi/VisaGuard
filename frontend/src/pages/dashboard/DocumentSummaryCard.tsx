import type { SnapshotResponse, WorkflowResultResponse } from '@/api/types'

type DocumentSummaryCardProps = {
  snapshot?: SnapshotResponse | null
  workflowResult?: WorkflowResultResponse
}

type SummaryItem = {
  label: string
  status: string
  detail: string
}

function hasAnyField(snapshot: SnapshotResponse | null | undefined, fields: string[]) {
  const payload = snapshot?.snapshot_payload ?? {}
  return fields.some((field) => payload[field] != null)
}

function buildSummaryItems(snapshot?: SnapshotResponse | null): SummaryItem[] {
  const provenanceMap = snapshot?.provenance_map ?? {}
  const hasManualEad = typeof provenanceMap.alien_registration_number === 'string' && provenanceMap.alien_registration_number.startsWith('ead:manual:')

  return [
    {
      label: 'I-20',
      status: hasAnyField(snapshot, ['sevis_id', 'school_name', 'major']) ? 'On file' : 'Missing',
      detail: hasAnyField(snapshot, ['sevis_id', 'school_name', 'major']) ? 'Student and program details loaded.' : 'Upload your most recent I-20 PDF.',
    },
    {
      label: 'EAD',
      status: hasAnyField(snapshot, ['alien_registration_number', 'card_end_date']) ? (hasManualEad ? 'Manual entry' : 'On file') : 'Missing',
      detail: hasAnyField(snapshot, ['alien_registration_number', 'card_end_date']) ? (hasManualEad ? 'Using your manual EAD details.' : 'Card details are available for evaluation.') : 'Add your EAD manually or upload an EAD image.',
    },
    {
      label: 'Offer letter',
      status: hasAnyField(snapshot, ['company_name', 'position_title', 'job_duties']) ? 'On file' : 'Missing',
      detail: hasAnyField(snapshot, ['company_name', 'position_title', 'job_duties']) ? 'Employment details are ready for policy review.' : 'Upload your signed offer letter PDF.',
    },
  ]
}

export function DocumentSummaryCard({ snapshot, workflowResult }: DocumentSummaryCardProps) {
  const items = buildSummaryItems(snapshot)

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Document and workflow summary</h2>
          <p className="mt-1 text-sm text-slate-600">
            Keep your intake current, then rerun the evaluation anytime your situation changes.
          </p>
        </div>
        <div className="text-sm text-slate-500">
          {workflowResult?.evaluation_date ? `Latest evaluation: ${workflowResult.evaluation_date}` : 'No evaluation run yet'}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {items.map((item) => (
          <article key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-900">{item.label}</h3>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700">{item.status}</span>
            </div>
            <p className="mt-3 text-sm text-slate-600">{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
