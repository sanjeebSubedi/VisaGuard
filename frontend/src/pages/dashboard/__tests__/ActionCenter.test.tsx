import { render, screen } from '@testing-library/react'

import { ActionCenter } from '@/pages/dashboard/ActionCenter'

describe('ActionCenter', () => {
  it('renders checklist items when actions are present', () => {
    render(<ActionCenter actions={['Report new employer to SEVP', 'Upload a signed offer letter']} />)

    expect(screen.getByText(/report new employer to sevp/i)).toBeInTheDocument()
    expect(screen.getByText(/upload a signed offer letter/i)).toBeInTheDocument()
  })

  it('renders a reassuring empty state when no actions are required', () => {
    render(<ActionCenter actions={[]} />)

    expect(screen.getByText(/all caught up/i)).toBeInTheDocument()
  })
})
