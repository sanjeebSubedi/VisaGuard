import { render, screen } from '@testing-library/react'
import { App } from '@/app/App'

describe('App', () => {
  it('renders the app shell with a user id control and live copilot sidebar on the dashboard', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /visaguard/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/user id/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/ask the dso copilot/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
  })
})
