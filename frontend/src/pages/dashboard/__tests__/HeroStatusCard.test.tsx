import { render, screen } from '@testing-library/react'

import { HeroStatusCard } from '@/pages/dashboard/HeroStatusCard'

describe('HeroStatusCard', () => {
  it('renders the overall state and audit summary with severity styling', () => {
    render(
      <HeroStatusCard
        record={{
          overall_state: 'IN_STATUS',
          severity: 'INFO',
          audit_summary: '52 days remaining on the OPT unemployment clock.',
          action_plan: [],
        }}
      />,      
    )

    expect(screen.getByText(/in status/i)).toBeInTheDocument()
    expect(screen.getByText(/52 days remaining/i)).toBeInTheDocument()
    expect(screen.getByTestId('hero-status-card')).toHaveClass('bg-emerald-500')
  })
})
