export function ManualEADForm() {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Manual EAD entry</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Alien Registration Number</span>
          <input className="rounded-xl border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Category</span>
          <input className="rounded-xl border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Card Start Date</span>
          <input type="date" className="rounded-xl border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Card End Date</span>
          <input type="date" className="rounded-xl border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700 md:col-span-2">
          <span>Card Number</span>
          <input className="rounded-xl border border-slate-300 px-3 py-2" />
        </label>
      </div>
    </section>
  )
}
