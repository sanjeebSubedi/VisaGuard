import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { ApiError } from '@/api/client'
import { DSOChatSidebar } from '@/components/chat/DSOChatSidebar'

const sendDSOChatMessage = vi.fn()

vi.mock('@/api/dso', async () => {
  const actual = await vi.importActual<typeof import('@/api/dso')>('@/api/dso')
  return {
    ...actual,
    sendDSOChatMessage: (...args: unknown[]) => sendDSOChatMessage(...args),
  }
})

function renderSidebar(userId = 'user0') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <DSOChatSidebar userId={userId} />
    </QueryClientProvider>,
  )
}

describe('DSOChatSidebar', () => {
  beforeEach(() => {
    sendDSOChatMessage.mockReset()
  })

  it('sends a message and renders the grounded response with citations', async () => {
    const user = userEvent.setup()
    sendDSOChatMessage.mockResolvedValueOnce({
      answer:
        'Federal rules allow multiple concurrent OPT jobs as long as each position is directly related to your major and properly reported.',
      citations: [
        {
          title: 'SEVP OPT Guidance',
          citation: 'SEVP Policy 1004-03',
          source_type: 'federal',
          excerpt: 'Students may have multiple employers while on standard OPT.',
          score: 0.91,
        },
      ],
      confidence: 'high',
      needs_human_escalation: false,
      answer_mode: 'general_policy',
    })

    renderSidebar()

    await user.type(screen.getByLabelText(/ask the dso copilot/i), 'Can I work two jobs on OPT?')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(sendDSOChatMessage).toHaveBeenCalledWith({
      userId: 'user0',
      message: 'Can I work two jobs on OPT?',
      chatHistory: [],
    })

    expect(await screen.findByText(/federal rules allow multiple concurrent opt jobs/i)).toBeInTheDocument()
    expect(screen.getByText(/sevp policy 1004-03/i)).toBeInTheDocument()
    expect(screen.getByText(/students may have multiple employers while on standard opt/i)).toBeInTheDocument()
  })

  it('shows a targeted message when the student has not run the compliance workflow yet', async () => {
    const user = userEvent.setup()
    sendDSOChatMessage.mockRejectedValueOnce(
      new ApiError('No workflow result found for user_id=user0. Run the compliance workflow first.', 404),
    )

    renderSidebar()

    await user.type(screen.getByLabelText(/ask the dso copilot/i), 'How many unemployment days do I have left?')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(
      await screen.findByText(/run the compliance workflow first so the copilot can load your current status/i),
    ).toBeInTheDocument()
  })

  it('disables the composer when no user id is selected', () => {
    renderSidebar('')

    expect(screen.getByLabelText(/ask the dso copilot/i)).toBeDisabled()
    expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled()
    expect(screen.getByText(/enter a user id to start chatting/i)).toBeInTheDocument()
  })

  it('keeps the user message visible when the request fails', async () => {
    const user = userEvent.setup()
    sendDSOChatMessage.mockRejectedValueOnce(new ApiError('DSO agent is temporarily unavailable. Please try again or contact your DSO.', 503))

    renderSidebar()

    await user.type(screen.getByLabelText(/ask the dso copilot/i), 'Do I need a travel signature?')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(await screen.findByText(/do i need a travel signature/i)).toBeInTheDocument()
    expect(await screen.findByText(/please try again in a moment/i)).toBeInTheDocument()
    await waitFor(() => expect(sendDSOChatMessage).toHaveBeenCalledTimes(1))
  })
})
