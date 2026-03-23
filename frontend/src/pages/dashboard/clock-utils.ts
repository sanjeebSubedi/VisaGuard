export type ClockView = {
  status: string
  limit_days?: number | null
  days_remaining?: number | null
  relevant_dates: Record<string, string>
}

export function formatClockName(clockKey: string) {
  return clockKey
    .split('_')
    .map((part) => part.toLowerCase())
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function describeClock(clockKey: string, clock: ClockView) {
  if (clock.limit_days) {
    const usedDays = Math.max(clock.limit_days - (clock.days_remaining ?? 0), 0)
    return {
      title: formatClockName(clockKey),
      subtitle: `${usedDays} of ${clock.limit_days} days used (${clock.days_remaining ?? 0} days remaining)`,
      progress: Math.min(Math.max((usedDays / clock.limit_days) * 100, 0), 100),
      detail: null,
    }
  }

  const totalWindowDays = deriveWindowDays(clock.relevant_dates)
  return {
    title: formatClockName(clockKey),
    subtitle: `${clock.days_remaining ?? 0} days remaining`,
    progress: totalWindowDays ? Math.min(Math.max((((totalWindowDays - (clock.days_remaining ?? 0)) / totalWindowDays) * 100), 0), 100) : 0,
    detail: totalWindowDays ? `${totalWindowDays} day window` : 'Countdown window',
  }
}

function deriveWindowDays(relevantDates: Record<string, string>) {
  const keys = Object.keys(relevantDates)
  const startKey = keys.find((key) => key.endsWith('_start'))
  const endKey = keys.find((key) => key.endsWith('_end'))
  if (!startKey || !endKey) {
    return null
  }

  const start = new Date(relevantDates[startKey])
  const end = new Date(relevantDates[endKey])
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return null
  }

  const millisPerDay = 1000 * 60 * 60 * 24
  return Math.round((end.getTime() - start.getTime()) / millisPerDay)
}
