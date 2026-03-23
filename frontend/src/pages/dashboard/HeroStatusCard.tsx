import type { WorkflowRunResponse } from '@/api/types'

type HeroStatusCardProps = {
  record: NonNullable<WorkflowRunResponse['final_compliance_record']>
}

const severityPillClasses: Record<string, string> = {
  INFO: 'border-emerald-400/30 bg-emerald-500/15 text-emerald-200',
  WARNING: 'border-amber-400/30 bg-amber-500/15 text-amber-100',
  CRITICAL: 'border-red-400/30 bg-red-500/15 text-red-100',
  VIOLATION: 'border-rose-400/30 bg-rose-600/20 text-rose-100',
}

export function HeroStatusCard({ record }: HeroStatusCardProps) {
  const severity = record.severity ?? 'INFO'
  const pillTone = severityPillClasses[severity] ?? severityPillClasses.INFO
  const confidencePoints = record.confidence_points ?? []

  return (
    <section
      data-testid="hero-status-card"
      className="rounded-3xl border border-slate-800 bg-slate-900/95 p-8 shadow-xl shadow-slate-950/30"
    >
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">Current status</p>
        <span
          data-testid="severity-pill"
          className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${pillTone}`}
        >
          {severity}
        </span>
      </div>
      <h2 className="mt-3 text-4xl font-bold text-slate-50">{record.overall_state.replace(/_/g, ' ')}</h2>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300">{record.audit_summary}</p>
      {confidencePoints.length ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {confidencePoints.map((point) => (
            <span
              key={point}
              className="inline-flex items-center rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1 text-xs font-medium text-slate-200"
            >
              <span aria-hidden="true" className="mr-2 text-sky-300">✓</span>
              {point}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  )
}
