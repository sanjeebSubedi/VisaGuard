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
        className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isRunning ? 'Running evaluation...' : 'Run evaluation'}
      </button>
    </div>
  )
}
