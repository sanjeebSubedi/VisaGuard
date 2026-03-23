import { describe, expect, it } from 'vitest'

import { describeClock } from '@/pages/dashboard/clock-utils'

describe('describeClock', () => {
  it('labels future reporting windows as opening later instead of active countdowns', () => {
    const view = describeClock(
      'reporting_window',
      {
        status: 'active',
        limit_days: null,
        days_remaining: 10,
        relevant_dates: {
          trigger_date: '2026-04-27',
          reporting_window_end: '2026-05-07',
        },
      },
      '2026-03-22',
    )

    expect(view.subtitle).toBe('Window opens Apr 27, 2026')
    expect(view.detail).toBe('Deadline: May 7, 2026')
  })

  it('labels future grace periods as beginning later', () => {
    const view = describeClock(
      'grace_period',
      {
        status: 'active',
        limit_days: null,
        days_remaining: 344,
        relevant_dates: {
          grace_period_start: '2026-12-31',
          grace_period_end: '2027-03-01',
        },
      },
      '2026-03-22',
    )

    expect(view.subtitle).toBe('Begins Dec 31, 2026')
    expect(view.detail).toBe('Ends Mar 1, 2027')
  })

  it('keeps active drawdown clocks on used and remaining wording', () => {
    const view = describeClock(
      'opt_unemployment',
      {
        status: 'active',
        limit_days: 90,
        days_remaining: 52,
        relevant_dates: {},
      },
      '2026-03-22',
    )

    expect(view.subtitle).toBe('38 of 90 days used (52 days remaining)')
    expect(view.detail).toBeNull()
  })
})
