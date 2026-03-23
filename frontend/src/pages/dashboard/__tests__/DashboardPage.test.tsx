import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { DashboardRoute } from '@/pages/dashboard/DashboardPage'
import { UserProvider } from '@/state/user-context'

const getLatestWorkflowResult = vi.fn()
const getSnapshot = vi.fn()
const runComplianceWorkflow = vi.fn()

vi.mock('@/api/workflows', async () => {
  const actual = await vi.importActual<typeof import('@/api/workflows')>('@/api/workflows')
  return {
    ...actual,
    getLatestWorkflowResult: (...args: unknown[]) => getLatestWorkflowResult(...args),
    runComplianceWorkflow: (...args: unknown[]) => runComplianceWorkflow(...args),
  }
})

vi.mock('@/api/intake', async () => {
  const actual = await vi.importActual<typeof import('@/api/intake')>('@/api/intake')
  return {
    ...actual,
    getSnapshot: (...args: unknown[]) => getSnapshot(...args),
  }
})

function renderRoute() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <UserProvider>
          <DashboardRoute />
        </UserProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('DashboardRoute', () => {
  beforeEach(() => {
    getLatestWorkflowResult.mockReset()
    getSnapshot.mockReset()
    runComplianceWorkflow.mockReset()
  })

  it('shows an empty state when no workflow result exists yet', async () => {
    getLatestWorkflowResult.mockRejectedValueOnce(new ApiError('Workflow result not found', 404))
    getSnapshot.mockRejectedValueOnce(new ApiError('Snapshot not found', 404))

    renderRoute()

    expect(await screen.findByText(/no compliance result yet/i)).toBeInTheDocument()
    expect(screen.getByText(/go to intake/i)).toBeInTheDocument()
    expect(screen.getByText(/upload your most recent i-20 pdf/i)).toBeInTheDocument()
  })

  it('renders hero, actions, and clocks when workflow data is present', async () => {
    getLatestWorkflowResult.mockResolvedValueOnce({
      user_id: 'user0',
      evaluation_date: '2026-03-22',
      final_compliance_record: {
        overall_state: 'IN_STATUS',
        severity: 'INFO',
        audit_summary: '52 days remaining on the OPT unemployment clock.',
        action_plan: ['Report any employer change within 10 days'],
      },
      timeline_status: {
        clocks: {
          opt_unemployment: {
            status: 'active',
            limit_days: 90,
            days_remaining: 52,
            relevant_dates: {},
          },
        },
      },
      policy_analysis: {},
      policy_verdict: {},
    })
    getSnapshot.mockResolvedValueOnce({
      user_id: 'user0',
      snapshot_payload: {
        sevis_id: 'N0012345678',
        alien_registration_number: 'A123456789',
        company_name: 'OpenAI',
      },
      field_eligibility_map: {},
      provenance_map: { alien_registration_number: 'ead:manual:alien_registration_number' },
      version: 1,
    })

    renderRoute()

    expect(await screen.findByText(/in status/i)).toBeInTheDocument()
    expect(screen.getByText(/report any employer change within 10 days/i)).toBeInTheDocument()
    expect(screen.getByText(/38 of 90 days used/i)).toBeInTheDocument()
    expect(screen.getByText(/latest evaluation: 2026-03-22/i)).toBeInTheDocument()
    expect(screen.getByText(/manual entry/i)).toBeInTheDocument()
  })

  it('disables the workflow run button while a refresh is in progress', async () => {
    const user = userEvent.setup()
    getLatestWorkflowResult.mockRejectedValueOnce(new ApiError('Workflow result not found', 404))
    getSnapshot.mockRejectedValueOnce(new ApiError('Snapshot not found', 404))
    runComplianceWorkflow.mockImplementationOnce(() => new Promise((resolve) => setTimeout(() => resolve({}), 50)))

    renderRoute()

    const button = await screen.findByRole('button', { name: /run evaluation/i })
    await user.click(button)

    expect(screen.getByRole('button', { name: /running evaluation/i })).toBeDisabled()
    await waitFor(() => expect(runComplianceWorkflow).toHaveBeenCalled())
  })
})
