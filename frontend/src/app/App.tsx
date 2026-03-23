import { AppShell } from '@/components/layout/AppShell'
import { UserProvider } from '@/state/user-context'

export function App() {
  return (
    <UserProvider>
      <AppShell>
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Compliance dashboard coming together</h2>
          <p className="mt-3 text-sm text-slate-600">
            We&apos;re wiring the status, actions, clocks, and intake flow into this shell next.
          </p>
        </section>
      </AppShell>
    </UserProvider>
  )
}
