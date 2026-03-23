import { describeClock, type ClockView } from '@/pages/dashboard/clock-utils'

type ComplianceClockListProps = {
  clocks: Record<string, ClockView>
  evaluationDate?: string
}

export function ComplianceClockList({ clocks, evaluationDate }: ComplianceClockListProps) {
  const visibleClocks = Object.entries(clocks).filter(([, clock]) => clock.status === 'active')

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/95 p-6 shadow-xl shadow-slate-950/30">
      <h2 className="text-lg font-semibold text-slate-50">Compliance Clocks</h2>

      <div className="mt-4 space-y-5">
        {visibleClocks.map(([clockKey, clock]) => {
          const view = describeClock(clockKey, clock, evaluationDate)

          return (
            <article key={clockKey} className="space-y-2">
              <div className="flex items-center justify-between gap-4">
                <h3 className="text-sm font-semibold text-slate-100">{view.title}</h3>
                <span className="text-sm text-slate-400">{view.subtitle}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-sky-500" style={{ width: `${view.progress}%` }} />
              </div>
              {view.detail ? <p className="text-xs text-slate-500">{view.detail}</p> : null}
            </article>
          )
        })}
      </div>
    </section>
  )
}
