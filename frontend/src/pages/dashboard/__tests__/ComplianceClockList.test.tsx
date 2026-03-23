import { render, screen } from '@testing-library/react'

import { ComplianceClockList } from '@/pages/dashboard/ComplianceClockList'

describe('ComplianceClockList', () => {
  it('shows active drawdown clocks with used and remaining day labels', () => {
    render(
      <ComplianceClockList
        clocks={{
          opt_unemployment: {
            status: 'active',
            limit_days: 90,
            days_remaining: 52,
            relevant_dates: {},
          },
          cap_gap: {
            status: 'not_applicable',
            relevant_dates: {},
          },
        }}
      />,
    )

    expect(screen.getByText(/opt unemployment/i)).toBeInTheDocument()
    expect(screen.getByText(/38 of 90 days used/i)).toBeInTheDocument()
    expect(screen.queryByText(/cap gap/i)).not.toBeInTheDocument()
  })

  it('renders a countdown-style label when limit_days is null', () => {
    render(
      <ComplianceClockList
        clocks={{
          grace_period: {
            status: 'active',
            limit_days: null,
            days_remaining: 45,
            relevant_dates: {
              grace_period_start: '2026-01-01',
              grace_period_end: '2026-03-02',
            },
          },
        }}
      />,
    )

    expect(screen.getByText(/grace period/i)).toBeInTheDocument()
    expect(screen.getByText(/45 days remaining/i)).toBeInTheDocument()
    expect(screen.getByText(/60 day window/i)).toBeInTheDocument()
  })
})
