import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Toaster } from 'sonner'
import { DisabledChatSidebar } from '@/components/chat/DisabledChatSidebar'

describe('DisabledChatSidebar', () => {
  it('shows a gated-feature toast when the disabled input area is clicked', async () => {
    const user = userEvent.setup()

    render(
      <>
        <DisabledChatSidebar />
        <Toaster />
      </>,
    )

    await user.click(screen.getByRole('button', { name: /dso copilot input is disabled/i }))

    expect(
      await screen.findByText(/the dso copilot is currently in beta and will be unlocked for your account soon/i),
    ).toBeInTheDocument()
  })
})
