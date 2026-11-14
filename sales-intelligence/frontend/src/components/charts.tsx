import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'
import { ResponsiveContainer } from 'recharts'
import { useTheme } from '../lib/theme'

// Categorical series colours, readable on both white and near-black.
export const PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#84cc16', '#f97316']

export function useChartStyle() {
  const { theme } = useTheme()
  const dark = theme === 'dark'
  return {
    grid: dark ? '#1f1f1f' : '#e5e5e5',
    axis: dark ? '#8a8a8a' : '#6b6b6b',
    tooltip: {
      backgroundColor: dark ? '#111111' : '#ffffff',
      border: `1px solid ${dark ? '#2a2a2a' : '#e5e5e5'}`,
      borderRadius: 8,
      fontSize: 12,
      color: dark ? '#e5e5e5' : '#171717',
      boxShadow: '0 12px 24px -12px rgb(0 0 0 / 0.45)',
    },
    label: { color: dark ? '#f5f5f5' : '#171717', fontWeight: 600 },
  }
}

export function ChartCard({
  title,
  subtitle,
  height = 280,
  isEmpty = false,
  emptyHint,
  action,
  children,
}: {
  title: string
  subtitle?: string
  height?: number
  isEmpty?: boolean
  emptyHint?: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center gap-2 text-center" style={{ height }}>
          <Inbox className="h-7 w-7 text-slate-300 dark:text-slate-600" aria-hidden />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">No data for this selection</p>
          <p className="max-w-xs text-xs text-slate-500 dark:text-slate-400">
            {emptyHint ?? 'Ingest transactions and run the Hadoop pipeline first.'}
          </p>
        </div>
      ) : (
        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            {children as never}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
