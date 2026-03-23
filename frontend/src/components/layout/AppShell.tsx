import type { ReactNode } from 'react'

import { Toaster } from 'sonner'

import { DisabledChatSidebar } from '@/components/chat/DisabledChatSidebar'
import { useUserId } from '@/state/use-user-id'

export function AppShell({ children }: { children: ReactNode }) {
  const { userId, setUserId } = useUserId()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">VisaGuard</h1>
            <p className="text-sm text-slate-600">Student compliance dashboard</p>
          </div>

          <div className="flex min-w-[16rem] flex-col gap-1">
            <label htmlFor="user-id" className="text-sm font-medium text-slate-700">
              User ID
            </label>
            <input
              id="user-id"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0"
            />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <main>{children}</main>
        <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
          <DisabledChatSidebar />
        </div>
      </div>
      <Toaster position="top-right" richColors />
    </div>
  )
}
