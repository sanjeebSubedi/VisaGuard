import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { IntakeRoute } from '@/pages/intake/IntakePage'
import { UserProvider } from '@/state/user-context'

const uploadDocument = vi.fn()
const createManualEadEntry = vi.fn()

vi.mock('@/api/intake', async () => {
  const actual = await vi.importActual<typeof import('@/api/intake')>('@/api/intake')
  return {
    ...actual,
    uploadDocument: (...args: unknown[]) => uploadDocument(...args),
    createManualEadEntry: (...args: unknown[]) => createManualEadEntry(...args),
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
    <QueryClientProvider client={queryClient}>
      <UserProvider>
        <IntakeRoute />
      </UserProvider>
    </QueryClientProvider>,
  )
}

describe('IntakeRoute', () => {
  beforeEach(() => {
    uploadDocument.mockReset()
    createManualEadEntry.mockReset()
  })

  it('renders the upload and manual entry forms', async () => {
    renderRoute()

    expect(screen.getByRole('heading', { name: /document intake/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/i-20 pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/offer letter pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/alien registration number/i)).toBeInTheDocument()
  })


  it('uploads an i-20 document for the selected user', async () => {
    const user = userEvent.setup()
    uploadDocument.mockResolvedValueOnce({ document_type: 'i20' })

    renderRoute()

    const file = new File(['pdf-bytes'], 'i20.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText(/i-20 pdf/i), file)
    await user.click(screen.getByRole('button', { name: /upload i-20/i }))

    expect(await screen.findByText(/document uploaded successfully/i)).toBeInTheDocument()
    expect(uploadDocument).toHaveBeenCalledWith({
      userId: 'user0',
      documentType: 'i20',
      file,
    })
  })

  it('submits a manual EAD entry and shows a success message', async () => {
    const user = userEvent.setup()
    createManualEadEntry.mockResolvedValueOnce({ document_type: 'ead' })

    renderRoute()

    await user.type(screen.getByLabelText(/alien registration number/i), 'A123456789')
    await user.type(screen.getByLabelText(/^category$/i), 'C03B')
    await user.type(screen.getByLabelText(/card start date/i), '2026-01-01')
    await user.type(screen.getByLabelText(/card end date/i), '2026-12-31')
    await user.type(screen.getByLabelText(/card number/i), 'EAD123')
    await user.click(screen.getByRole('button', { name: /save manual ead/i }))

    expect(await screen.findByText(/manual ead saved/i)).toBeInTheDocument()
    expect(createManualEadEntry).toHaveBeenCalledWith({
      userId: 'user0',
      alienRegistrationNumber: 'A123456789',
      category: 'C03B',
      cardStartDate: '2026-01-01',
      cardEndDate: '2026-12-31',
      cardNumber: 'EAD123',
    })
  })
})
