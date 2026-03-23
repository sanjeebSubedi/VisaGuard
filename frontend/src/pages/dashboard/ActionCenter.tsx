type ActionCenterProps = {
  actions: string[]
}

export function ActionCenter({ actions }: ActionCenterProps) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/95 p-6 shadow-xl shadow-slate-950/30">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-50">Action Center</h2>
      </div>

      {actions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">All caught up! No actions required at this time.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {actions.map((action) => (
            <li key={action} className="flex items-start gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-200">
              <span className="mt-0.5 inline-block size-5 rounded-full border border-sky-400/50 bg-sky-500/10" aria-hidden="true" />
              <span>{action}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
