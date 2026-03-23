import { render, screen } from '@testing-library/react'
import { App } from '@/app/App'

describe('App', () => {
  it('renders the root shell heading', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /visaguard/i })).toBeInTheDocument()
  })
})
