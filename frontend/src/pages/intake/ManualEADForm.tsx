import { useState } from 'react'

export type ManualEadValues = {
  alienRegistrationNumber: string
  category: string
  cardStartDate: string
  cardEndDate: string
  cardNumber: string
}

type ManualEADFormProps = {
  onSubmit?: (values: ManualEadValues) => void
  isSubmitting?: boolean
}

const initialValues: ManualEadValues = {
  alienRegistrationNumber: '',
  category: '',
  cardStartDate: '',
  cardEndDate: '',
  cardNumber: '',
}

export function ManualEADForm({ onSubmit, isSubmitting = false }: ManualEADFormProps) {
  const [values, setValues] = useState(initialValues)

  return (
    <form
      className="rounded-3xl border border-slate-800 bg-slate-900/95 p-6 shadow-xl shadow-slate-950/30"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit?.(values)
      }}
    >
      <h2 className="text-lg font-semibold text-slate-50">Manual EAD entry</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm text-slate-300">
          <span>Alien Registration Number</span>
          <input
            value={values.alienRegistrationNumber}
            onChange={(event) => setValues((current) => ({ ...current, alienRegistrationNumber: event.target.value }))}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-300">
          <span>Category</span>
          <input
            value={values.category}
            onChange={(event) => setValues((current) => ({ ...current, category: event.target.value }))}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-300">
          <span>Card Start Date</span>
          <input
            type="date"
            value={values.cardStartDate}
            onChange={(event) => setValues((current) => ({ ...current, cardStartDate: event.target.value }))}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-300">
          <span>Card End Date</span>
          <input
            type="date"
            value={values.cardEndDate}
            onChange={(event) => setValues((current) => ({ ...current, cardEndDate: event.target.value }))}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-300 md:col-span-2">
          <span>Card Number</span>
          <input
            value={values.cardNumber}
            onChange={(event) => setValues((current) => ({ ...current, cardNumber: event.target.value }))}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500"
          />
        </label>
      </div>
      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-4 rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {isSubmitting ? 'Saving...' : 'Save manual EAD'}
      </button>
    </form>
  )
}
