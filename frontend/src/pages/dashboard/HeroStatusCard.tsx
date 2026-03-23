import type { WorkflowRunResponse } from '@/api/types'

type HeroStatusCardProps = {
  record: NonNullable<WorkflowRunResponse['final_compliance_record']>
}

const severityClasses: Record<string, string> = {
  INFO: 'bg-emerald-500 text-white',
  WARNING: 'bg-amber-400 text-slate-950',
  CRITICAL: 'bg-red-500 text-white',
  VIOLATION: 'bg-rose-700 text-white',
}

export function HeroStatusCard({ record }: HeroStatusCardProps) {
  const tone = severityClasses[record.severity ?? 'INFO'] ?? severityClasses.INFO

  return (
    <section data-testid="hero-status-card" className={`rounded-3xl p-8 shadow-sm ${tone}`}>
      <p className="text-sm font-medium uppercase tracking-[0.2em] opacity-90">Current status</p>
      <h2 className="mt-3 text-4xl font-bold">{record.overall_state.replaceAll('_', ' ')}</h2>
      <p className="mt-4 max-w-3xl text-sm leading-6 opacity-95">{record.audit_summary}</p>
    </section>
  )
}
