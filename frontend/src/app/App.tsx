import { AppProviders } from '@/app/providers'
import { AppRoutes } from '@/app/routes'
import { AppShell } from '@/components/layout/AppShell'
import { UserProvider } from '@/state/user-context'

export function App() {
  return (
    <AppProviders>
      <UserProvider>
        <AppShell>
          <AppRoutes />
        </AppShell>
      </UserProvider>
    </AppProviders>
  )
}
