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

export function describeClock(clockKey: string, clock: ClockView, evaluationDate?: string) {
  if (clock.limit_days) {
    const usedDays = Math.max(clock.limit_days - (clock.days_remaining ?? 0), 0)
    return {
      title: formatClockName(clockKey),
      subtitle: `${usedDays} of ${clock.limit_days} days used (${clock.days_remaining ?? 0} days remaining)`,
      progress: Math.min(Math.max((usedDays / clock.limit_days) * 100, 0), 100),
      detail: null,
    }
  }

  const futureWindow = describeFutureWindow(clock.relevant_dates, evaluationDate)
  if (futureWindow) {
    return {
      title: formatClockName(clockKey),
      subtitle: futureWindow.subtitle,
      progress: 0,
      detail: futureWindow.detail,
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

function describeFutureWindow(relevantDates: Record<string, string>, evaluationDate?: string) {
  if (!evaluationDate) {
    return null
  }

  const evaluation = parseIsoDate(evaluationDate)
  if (!evaluation) {
    return null
  }

  const triggerDate = parseIsoDate(relevantDates.trigger_date)
  if (triggerDate && triggerDate > evaluation) {
    return {
      subtitle: `Window opens ${formatDate(triggerDate)}`,
      detail: relevantDates.reporting_window_end ? `Deadline: ${formatDateString(relevantDates.reporting_window_end)}` : 'Future window',
    }
  }

  const startKey = Object.keys(relevantDates).find((key) => key.endsWith('_start'))
  if (!startKey) {
    return null
  }

  const startDate = parseIsoDate(relevantDates[startKey])
  if (!startDate || startDate <= evaluation) {
    return null
  }

  const endKey = Object.keys(relevantDates).find((key) => key.endsWith('_end'))
  return {
    subtitle: `Begins ${formatDate(startDate)}`,
    detail: endKey ? `Ends ${formatDateString(relevantDates[endKey])}` : 'Future window',
  }
}

function deriveWindowDays(relevantDates: Record<string, string>) {
  const keys = Object.keys(relevantDates)
  const startKey = keys.find((key) => key.endsWith('_start'))
  const endKey = keys.find((key) => key.endsWith('_end'))
  if (!startKey || !endKey) {
    return null
  }

  const start = parseIsoDate(relevantDates[startKey])
  const end = parseIsoDate(relevantDates[endKey])
  if (!start || !end) {
    return null
  }

  const millisPerDay = 1000 * 60 * 60 * 24
  return Math.round((end.getTime() - start.getTime()) / millisPerDay)
}

function parseIsoDate(value?: string) {
  if (!value) {
    return null
  }

  const parsed = new Date(`${value}T00:00:00Z`)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed
}

function formatDateString(value?: string) {
  const parsed = parseIsoDate(value)
  return parsed ? formatDate(parsed) : value ?? 'Unknown date'
}

function formatDate(value: Date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(value)
}
