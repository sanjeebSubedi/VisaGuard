type WorkflowRunControlProps = {
  isRunning?: boolean
  onRun?: () => void
  isDisabled?: boolean
}

export function WorkflowRunControl({ isRunning = false, onRun, isDisabled = false }: WorkflowRunControlProps) {
  return (
    <div className="flex items-center justify-end">
      <button
        type="button"
        disabled={isRunning || isDisabled}
        onClick={onRun}
        className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {isRunning ? 'Running evaluation...' : 'Run evaluation'}
      </button>
    </div>
  )
}
