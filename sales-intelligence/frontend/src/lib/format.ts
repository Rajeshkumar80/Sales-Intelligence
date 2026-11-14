export const money = (value: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value)

export const moneyCompact = (value: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(value)

export const count = (value: number): string => new Intl.NumberFormat('en-US').format(value)

export const compact = (value: number): string =>
  new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value)

export const dateTime = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'

export const dateOnly = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' }) : '—'

export const duration = (ms: number | null): string => {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${ms} ms`
  const seconds = Math.round(ms / 100) / 10
  if (seconds < 60) return `${seconds} s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

export const monthLabel = (value: string): string => {
  const [year, month] = value.split('-')
  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
}

export const pct = (value: number): string => `${value.toFixed(1)}%`
