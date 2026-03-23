import { Link } from 'react-router-dom'

export function DashboardEmptyState() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">No compliance result yet</h2>
      <p className="mt-3 text-sm text-slate-600">
        Add your documents or manual EAD entry first, then run the evaluation to see your current status.
      </p>
      <Link
        to="/intake"
        className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
      >
        Go to intake
      </Link>
    </section>
  )
}
