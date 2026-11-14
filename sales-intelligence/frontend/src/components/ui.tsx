import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react'

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500 dark:text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </div>
  )
}

export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Something went wrong'
  return (
    <div className="card border-rose-200 bg-rose-50 dark:border-rose-900/60 dark:bg-rose-950/30" role="alert">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" />
        <div className="flex-1">
          <p className="text-sm font-medium text-rose-800 dark:text-rose-200">Request failed</p>
          <p className="mt-1 text-sm text-rose-700 dark:text-rose-300">{message}</p>
        </div>
        {onRetry && (
          <button type="button" className="btn-secondary" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyBlock({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-2 py-14 text-center">
      <Inbox className="h-7 w-7 text-slate-300 dark:text-slate-600" aria-hidden />
      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{title}</p>
      {hint && <p className="max-w-md text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">{hint}</p>}
      {action}
    </div>
  )
}

export function KpiCard({ label, value, hint, icon }: { label: string; value: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="card">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">{label}</p>
        {icon && <span className="text-slate-400 dark:text-slate-500">{icon}</span>}
      </div>
      <p className="mt-2.5 text-[26px] font-semibold leading-none tracking-tight tabular-nums text-slate-900 dark:text-white">
        {value}
      </p>
      {hint && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  )
}

const tones = {
  neutral: 'bg-slate-100 text-slate-600 ring-slate-600/10 dark:bg-white/[0.06] dark:text-slate-300 dark:ring-white/10',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20',
  warning: 'bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20',
  danger: 'bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20',
  info: 'bg-brand-50 text-brand-700 ring-brand-600/20 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-400/20',
}

export function Badge({ tone = 'neutral', children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${tones[tone]}`}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === 'SUCCEEDED' || status === 'ok' || status === 'RUNNING'
      ? 'success'
      : status === 'FAILED' || status === 'error'
        ? 'danger'
        : status === 'QUEUED'
          ? 'info'
          : 'neutral'
  return <Badge tone={tone}>{status}</Badge>
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-semibold leading-tight tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: readonly { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="inline-flex flex-wrap rounded-lg border border-slate-200 bg-slate-50 p-0.5 dark:border-slate-800 dark:bg-white/[0.03]">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-[6px] px-2.5 py-1 text-xs font-medium capitalize transition ${
            value === option.value
              ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-800 dark:text-white'
              : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
