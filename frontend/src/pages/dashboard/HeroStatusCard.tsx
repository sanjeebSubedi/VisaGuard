import type { WorkflowRunResponse } from '@/api/types'

type HeroStatusCardProps = {
  record: NonNullable<WorkflowRunResponse['final_compliance_record']>
}

const severityClasses: Record<string, string> = {
  INFO: 'bg-emerald-500 text-white shadow-emerald-950/30',
  WARNING: 'bg-amber-400 text-slate-950 shadow-amber-950/30',
  CRITICAL: 'bg-red-500 text-white shadow-red-950/30',
  VIOLATION: 'bg-rose-700 text-white shadow-rose-950/30',
}

export function HeroStatusCard({ record }: HeroStatusCardProps) {
  const tone = severityClasses[record.severity ?? 'INFO'] ?? severityClasses.INFO

  return (
    <section data-testid="hero-status-card" className={`rounded-3xl p-8 shadow-2xl ${tone}`}>
      <p className="text-sm font-medium uppercase tracking-[0.2em] opacity-90">Current status</p>
      <h2 className="mt-3 text-4xl font-bold">{record.overall_state.replace(/_/g, ' ')}</h2>
      <p className="mt-4 max-w-3xl text-sm leading-6 opacity-95">{record.audit_summary}</p>
    </section>
  )
}
