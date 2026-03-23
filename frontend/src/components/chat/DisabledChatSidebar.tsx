import { toast } from 'sonner'

export function DisabledChatSidebar() {
  return (
    <aside className="flex h-full min-h-[28rem] flex-col rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">DSO Copilot</p>
        <h2 className="mt-2 text-lg font-semibold text-slate-900">Your compliance guide</h2>
        <p className="mt-2 text-sm text-slate-600">
          The DSO Copilot is coming soon. For now, use the dashboard and intake tools to update your record.
        </p>
      </div>

      <div className="mt-6 flex-1 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
        Hi! I will soon be able to explain your status, deadlines, and school-specific next steps.
      </div>

      <button
        type="button"
        aria-label="DSO Copilot input is disabled"
        className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-100 px-4 py-3 text-left text-sm text-slate-500"
        onClick={() => {
          toast.info('The DSO Copilot is currently in beta and will be unlocked for your account soon.')
        }}
      >
        Ask the DSO Copilot a question...
      </button>

      <button
        type="button"
        disabled
        className="mt-3 rounded-2xl bg-slate-200 px-4 py-3 text-sm font-medium text-slate-500"
      >
        Send
      </button>
    </aside>
  )
}
