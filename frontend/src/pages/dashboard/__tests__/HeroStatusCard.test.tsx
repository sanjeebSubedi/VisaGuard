import { render, screen } from '@testing-library/react'

import { HeroStatusCard } from '@/pages/dashboard/HeroStatusCard'

describe('HeroStatusCard', () => {
  it('renders the overall state, polished summary, confidence points, and a compact severity pill', () => {
    render(
      <HeroStatusCard
        record={{
          overall_state: 'IN_STATUS',
          severity: 'INFO',
          audit_summary: 'Your role is directly related to your major, and your timeline is well within the standard OPT limits.',
          confidence_points: ['52 days remaining on OPT', 'Job directly relates to your major'],
          action_plan: [],
        }}
      />,
    )

    expect(screen.getByText(/in status/i)).toBeInTheDocument()
    expect(screen.getByText(/your role is directly related/i)).toBeInTheDocument()
    expect(screen.getByText(/52 days remaining on opt/i)).toBeInTheDocument()
    expect(screen.getByText(/job directly relates to your major/i)).toBeInTheDocument()
    expect(screen.getByText(/info/i)).toBeInTheDocument()
    expect(screen.getByTestId('hero-status-card')).toHaveClass('bg-slate-900/95')
    expect(screen.getByTestId('severity-pill')).toHaveClass('bg-emerald-500/15')
  })
})
