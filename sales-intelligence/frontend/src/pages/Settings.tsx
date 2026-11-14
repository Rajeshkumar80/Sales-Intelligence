import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Info, Moon, Sun } from 'lucide-react'
import { api } from '../api/client'
import type { Health, Settings as SettingsData } from '../api/types'
import { Badge, ErrorBlock, SectionHeader, Spinner, StatusBadge } from '../components/ui'
import { dateTime } from '../lib/format'
import { useTheme } from '../lib/theme'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <span className="text-sm text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right text-sm font-medium text-slate-800 dark:text-slate-200">{value}</span>
    </div>
  )
}

export default function Settings() {
  const { theme, toggle } = useTheme()
  const health = useQuery({ queryKey: ['health-deep'], queryFn: () => api<Health>('/api/health?deep=true'), staleTime: 30_000 })
  const settings = useQuery({ queryKey: ['settings'], queryFn: () => api<SettingsData>('/api/settings') })

  if (settings.isLoading) return <Spinner label="Reading configuration…" />
  if (settings.error) return <ErrorBlock error={settings.error} onRetry={() => void settings.refetch()} />

  const data = settings.data!
  const healthData = health.data
  const components = healthData?.components

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Settings & diagnostics"
        subtitle="Read-only runtime configuration. Secrets are loaded from backend/.env and are never returned by the API."
        action={
          health.isLoading ? (
            <Badge tone="neutral">Checking services…</Badge>
          ) : healthData ? (
            <Badge tone={healthData.status === 'ok' ? 'success' : 'warning'}>{healthData.status}</Badge>
          ) : (
            <Badge tone="warning">Services unavailable</Badge>
          )
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
        <div>
          <p className="text-[13px] font-medium text-slate-800 dark:text-slate-100">Note</p>
          <p className="mt-0.5 text-[13px] text-slate-500 dark:text-slate-400">
            Hadoop + Hive + MongoDB Atlas. Demo values are produced by the pipeline, never hardcoded.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-2 text-sm font-semibold">Services</h3>
          {health.isLoading && <Spinner label="Checking MongoDB and Hive…" />}
          {health.error && <ErrorBlock error={health.error} onRetry={() => void health.refetch()} />}
          {components && (
            <>
              <Row label="MongoDB Atlas" value={<StatusBadge status={components.mongodb.status} />} />
              <Row label="Database" value={components.mongodb.database ?? '—'} />
              <Row label="Documents in transactions" value={components.mongodb.transactions ?? '—'} />
              <Row label="HiveServer2" value={<StatusBadge status={components.hive.status === 'ok' ? 'ok' : 'error'} />} />
              <Row label="Hive JDBC" value={<span className="font-mono text-xs">{components.hive.url}</span>} />
              <Row label="MapReduce jar built" value={<StatusBadge status={components.hadoop.jar_built ? 'ok' : 'error'} />} />
              <Row label="Hadoop binary" value={<span className="max-w-[240px] truncate font-mono text-xs">{components.hadoop.hadoop_bin}</span>} />
              {healthData && <Row label="Server time" value={dateTime(healthData.server_time)} />}
              {components.mongodb.error && (
                <p className="mt-2 rounded-lg bg-rose-50 p-2 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                  {components.mongodb.error}
                </p>
              )}
            </>
          )}
        </div>

        <div className="card">
          <h3 className="mb-2 text-sm font-semibold">Pipeline configuration</h3>
          <Row label="Rows per batch" value={data.batch_size.toLocaleString()} />
          <Row label="Simulator interval" value={`${data.simulator.interval_seconds}s`} />
          <Row label="Simulator batch" value={`${data.simulator.batch_size} rows/tick`} />
          <Row label="CSV limits" value={`${data.csv.max_mb} MB · ${data.csv.max_rows.toLocaleString()} rows`} />
          <Row label="HDFS input" value={<span className="font-mono text-xs">{data.hdfs.input}</span>} />
          <Row label="HDFS revenue" value={<span className="font-mono text-xs">{data.hdfs.revenue}</span>} />
          <Row label="Execution mode" value={data.execution_mode} />
        </div>

        <div className="card">
          <h3 className="mb-2 text-sm font-semibold">Appearance</h3>
          <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">Theme preference is stored in your browser.</p>
          <button type="button" className="btn-secondary" onClick={toggle}>
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            Switch to {theme === 'dark' ? 'light' : 'dark'} theme
          </button>
        </div>

        <div className="card">
          <h3 className="mb-2 text-sm font-semibold">API documentation</h3>
          <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
            FastAPI exposes the full OpenAPI contract for the viva demonstration.
          </p>
          <a className="btn-secondary" href="/docs" target="_blank" rel="noreferrer">
            <ExternalLink className="h-4 w-4" /> Open /docs
          </a>
        </div>
      </div>
    </div>
  )
}
