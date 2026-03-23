import { render, screen } from '@testing-library/react'
import { App } from '@/app/App'

describe('App', () => {
  it('renders the app shell with a user id control and disabled copilot sidebar', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /visaguard/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/user id/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /dso copilot input is disabled/i })).toBeInTheDocument()
  })
})
