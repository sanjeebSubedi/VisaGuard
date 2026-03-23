import { Link } from 'react-router-dom'

export function DashboardEmptyState() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-700 bg-slate-900/95 p-8 text-center shadow-xl shadow-slate-950/30">
      <h2 className="text-xl font-semibold text-slate-50">No compliance result yet</h2>
      <p className="mt-3 text-sm text-slate-400">
        Add your documents or manual EAD entry first, then run the evaluation to see your current status.
      </p>
      <Link
        to="/intake"
        className="mt-5 inline-flex rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
      >
        Go to intake
      </Link>
    </section>
  )
}
