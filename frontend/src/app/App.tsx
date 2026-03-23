import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { UserProvider } from '@/state/user-context'

export function App() {
  return (
    <UserProvider>
      <AppShell>
        <DashboardPage />
      </AppShell>
    </UserProvider>
  )
}
