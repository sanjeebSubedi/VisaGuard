import { useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { ApiError } from '@/api/client'
import { sendDSOChatMessage } from '@/api/dso'
import type { DSOCitation, DSOChatTurn } from '@/api/types'

type AssistantMessage = {
  role: 'assistant'
  content: string
  citations?: DSOCitation[]
}

type Message = DSOChatTurn | AssistantMessage

type DSOChatSidebarProps = {
  userId: string
}

function normalizeErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 404) {
    return 'Run the compliance workflow first so the Copilot can load your current status.'
  }
  if (error instanceof ApiError && error.status === 503) {
    return 'The DSO Copilot is temporarily unavailable. Please try again in a moment.'
  }
  if (error instanceof ApiError) {
    return error.message
  }
  return 'Something went wrong while contacting the DSO Copilot. Please try again.'
}

export function DSOChatSidebar({ userId }: DSOChatSidebarProps) {
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const chatHistory = useMemo<DSOChatTurn[]>(() => messages.map((message) => ({ role: message.role, content: message.content })), [messages])

  const mutation = useMutation({
    mutationFn: ({ message, history }: { message: string; history: DSOChatTurn[] }) =>
      sendDSOChatMessage({
        userId,
        message,
        chatHistory: history,
      }),
    onSuccess: (response) => {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
        },
      ])
      setErrorMessage(null)
    },
    onError: (error) => {
      setErrorMessage(normalizeErrorMessage(error))
    },
  })

  const canSend = userId.trim().length > 0 && draft.trim().length > 0 && !mutation.isPending

  const handleSend = async () => {
    const message = draft.trim()
    if (!message || !userId.trim()) {
      return
    }

    const history = [...chatHistory]
    setMessages((current) => [...current, { role: 'user', content: message }])
    setDraft('')
    setErrorMessage(null)
    try {
      await mutation.mutateAsync({ message, history })
    } catch {
      // Error state is handled by the mutation callbacks.
    }
  }

  return (
    <aside className="flex h-full min-h-[28rem] flex-col rounded-3xl border border-slate-800 bg-slate-900/95 p-5 shadow-2xl shadow-slate-950/40">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300/80">DSO Copilot</p>
        <h2 className="mt-2 text-lg font-semibold text-slate-50">Your compliance guide</h2>
        <p className="mt-2 text-sm text-slate-400">
          Ask about your current status, school processes, or common OPT questions. Answers stay grounded in your latest evaluation and source material.
        </p>
      </div>

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-400">Ask about travel, reporting deadlines, employer changes, or what your current status means.</p>
        ) : null}

        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className="space-y-2">
            <div
              className={message.role === 'user'
                ? 'ml-auto max-w-[85%] rounded-2xl bg-sky-500/20 px-4 py-3 text-sm text-sky-50'
                : 'max-w-[90%] rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-100'}
            >
              {message.content}
            </div>
            {'citations' in message && message.citations && message.citations.length > 0 ? (
              <div className="space-y-2 pl-1">
                {message.citations.map((citation, citationIndex) => (
                  <div key={`${citation.citation}-${citationIndex}`} className="rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs text-slate-300">
                    <p className="font-medium text-slate-200">{citation.title}</p>
                    <p className="mt-1 text-sky-200">{citation.citation}</p>
                    <p className="mt-1 text-slate-400">{citation.excerpt}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ))}

        {mutation.isPending ? <p className="text-sm text-slate-400">Thinking...</p> : null}
        {errorMessage ? <p className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{errorMessage}</p> : null}
      </div>

      <div className="mt-4 space-y-3">
        <label htmlFor="dso-chat-input" className="text-sm font-medium text-slate-300">
          Ask the DSO Copilot
        </label>
        <textarea
          id="dso-chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!userId.trim() || mutation.isPending}
          placeholder={userId.trim() ? 'Can I work two jobs on OPT?' : 'Enter a user ID to start chatting'}
          className="min-h-28 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
        />
        {!userId.trim() ? <p className="text-sm text-slate-500">Enter a user ID to start chatting.</p> : null}
        <button
          type="button"
          onClick={() => { void handleSend() }}
          disabled={!canSend}
          className="w-full rounded-2xl border border-sky-500/40 bg-sky-500/15 px-4 py-3 text-sm font-medium text-sky-100 transition hover:bg-sky-500/25 disabled:cursor-not-allowed disabled:border-slate-800 disabled:bg-slate-800 disabled:text-slate-500"
        >
          {mutation.isPending ? 'Sending...' : 'Send message'}
        </button>
      </div>
    </aside>
  )
}
