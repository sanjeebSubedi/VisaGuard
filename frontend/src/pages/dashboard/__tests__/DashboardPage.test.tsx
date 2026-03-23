import { render, screen } from '@testing-library/react'

import { DashboardPage } from '@/pages/dashboard/DashboardPage'

describe('DashboardPage', () => {
  it('shows an empty state when no workflow result exists yet', () => {
    render(<DashboardPage />)

    expect(screen.getByText(/no compliance result yet/i)).toBeInTheDocument()
    expect(screen.getByText(/go to intake/i)).toBeInTheDocument()
  })

  it('renders hero, actions, and clocks when workflow data is present', () => {
    render(
      <DashboardPage
        workflowResult={{
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
        }}
      />,
    )

    expect(screen.getByText(/in status/i)).toBeInTheDocument()
    expect(screen.getByText(/report any employer change within 10 days/i)).toBeInTheDocument()
    expect(screen.getByText(/38 of 90 days used/i)).toBeInTheDocument()
  })

  it('disables the workflow run button while a refresh is in progress', () => {
    render(<DashboardPage isRunningWorkflow />)

    expect(screen.getByRole('button', { name: /running evaluation/i })).toBeDisabled()
  })
})
