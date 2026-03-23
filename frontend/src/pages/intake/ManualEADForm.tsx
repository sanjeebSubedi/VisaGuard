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
      className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit?.(values)
      }}
    >
      <h2 className="text-lg font-semibold text-slate-900">Manual EAD entry</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Alien Registration Number</span>
          <input
            value={values.alienRegistrationNumber}
            onChange={(event) => setValues((current) => ({ ...current, alienRegistrationNumber: event.target.value }))}
            className="rounded-xl border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Category</span>
          <input
            value={values.category}
            onChange={(event) => setValues((current) => ({ ...current, category: event.target.value }))}
            className="rounded-xl border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Card Start Date</span>
          <input
            type="date"
            value={values.cardStartDate}
            onChange={(event) => setValues((current) => ({ ...current, cardStartDate: event.target.value }))}
            className="rounded-xl border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700">
          <span>Card End Date</span>
          <input
            type="date"
            value={values.cardEndDate}
            onChange={(event) => setValues((current) => ({ ...current, cardEndDate: event.target.value }))}
            className="rounded-xl border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-700 md:col-span-2">
          <span>Card Number</span>
          <input
            value={values.cardNumber}
            onChange={(event) => setValues((current) => ({ ...current, cardNumber: event.target.value }))}
            className="rounded-xl border border-slate-300 px-3 py-2"
          />
        </label>
      </div>
      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isSubmitting ? 'Saving...' : 'Save manual EAD'}
      </button>
    </form>
  )
}
