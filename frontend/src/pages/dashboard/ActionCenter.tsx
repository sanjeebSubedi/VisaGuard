type ActionCenterProps = {
  actions: string[]
}

export function ActionCenter({ actions }: ActionCenterProps) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Action Center</h2>
      </div>

      {actions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">All caught up! No actions required at this time.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {actions.map((action) => (
            <li key={action} className="flex items-start gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <span className="mt-0.5 inline-block size-5 rounded-full border border-slate-300" aria-hidden="true" />
              <span>{action}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
