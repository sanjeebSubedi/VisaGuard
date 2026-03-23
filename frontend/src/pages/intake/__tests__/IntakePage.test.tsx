import { render, screen } from '@testing-library/react'

import { IntakePage } from '@/pages/intake/IntakePage'

describe('IntakePage', () => {
  it('renders the upload and manual entry forms', () => {
    render(<IntakePage />)

    expect(screen.getByRole('heading', { name: /document intake/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/i-20 pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/offer letter pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/alien registration number/i)).toBeInTheDocument()
  })

  it('shows success and error message slots when provided', () => {
    render(
      <IntakePage
        uploadMessage="I-20 uploaded successfully"
        eadMessage="Manual EAD saved"
        errorMessage="Offer letter upload failed"
      />,
    )

    expect(screen.getByText(/i-20 uploaded successfully/i)).toBeInTheDocument()
    expect(screen.getByText(/manual ead saved/i)).toBeInTheDocument()
    expect(screen.getByText(/offer letter upload failed/i)).toBeInTheDocument()
  })
})
