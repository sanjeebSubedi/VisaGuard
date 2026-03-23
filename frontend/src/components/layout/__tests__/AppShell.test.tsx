import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AppShell } from '@/components/layout/AppShell'
import { UserProvider } from '@/state/user-context'

vi.mock('@/api/dso', () => ({
  sendDSOChatMessage: vi.fn(),
}))

function renderShell(pathname: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <QueryClientProvider client={queryClient}>
        <UserProvider>
          <AppShell>
            <div>Page content</div>
          </AppShell>
        </UserProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  it('shows the live chat composer on the dashboard route', () => {
    renderShell('/')

    expect(screen.getByLabelText(/ask the dso copilot/i)).toBeInTheDocument()
  })

  it('keeps the disabled chat sidebar on intake', () => {
    renderShell('/intake')

    expect(screen.getByRole('button', { name: /dso copilot input is disabled/i })).toBeInTheDocument()
  })
})
