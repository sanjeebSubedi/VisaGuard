import type { ReactNode } from 'react'

import { NavLink } from 'react-router-dom'
import { Toaster } from 'sonner'

import { DisabledChatSidebar } from '@/components/chat/DisabledChatSidebar'
import { useUserId } from '@/state/use-user-id'

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded-full border px-4 py-2 text-sm font-medium transition',
    isActive
      ? 'border-sky-400/60 bg-sky-500/20 text-sky-100'
      : 'border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:bg-slate-800 hover:text-slate-100',
  ].join(' ')

export function AppShell({ children }: { children: ReactNode }) {
  const { userId, setUserId } = useUserId()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6">
            <div>
              <h1 className="text-2xl font-semibold text-slate-50">VisaGuard</h1>
              <p className="text-sm text-slate-400">Student compliance dashboard</p>
            </div>

            <nav className="flex items-center gap-2" aria-label="Primary">
              <NavLink to="/" end className={navLinkClassName}>
                Dashboard
              </NavLink>
              <NavLink to="/intake" className={navLinkClassName}>
                Intake
              </NavLink>
            </nav>
          </div>

          <div className="flex min-w-[16rem] flex-col gap-1">
            <label htmlFor="user-id" className="text-sm font-medium text-slate-300">
              User ID
            </label>
            <input
              id="user-id"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-sky-500"
            />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <main className="min-w-0">{children}</main>
        <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
          <DisabledChatSidebar />
        </div>
      </div>
      <Toaster position="top-right" richColors theme="dark" />
    </div>
  )
}
