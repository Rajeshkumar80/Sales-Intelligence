import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, CircleDashed, Play, XCircle } from 'lucide-react'
import { api } from '../api/client'
import type { Job } from '../api/types'
import { Badge, ErrorBlock, SectionHeader, Spinner, StatusBadge } from '../components/ui'
import { count, dateTime, duration } from '../lib/format'

const stageLabels: Record<string, string> = {
  claim: 'Claim rows',
  hdfs: 'HDFS write',
  mapreduce: 'MapReduce job',
  hive_fact: 'Hive fact table',
  hive_aggregates: 'Hive aggregates',
  reconcile: 'Reconciliation',
}

export default function Jobs() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)
  const [batchSize, setBatchSize] = useState('1000')

  const status = useQuery({
    queryKey: ['processing'],
    queryFn: () => api<{ running: boolean; job: Job | null }>('/api/sales/processing/status'),
    refetchInterval: (query) => (query.state.data?.running ? 3_000 : 15_000),
  })

  const history = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api<{ items: Job[] }>('/api/sales/jobs?limit=20'),
    refetchInterval: 15_000,
  })

  const detail = useQuery({
    queryKey: ['job', selected],
    queryFn: () => api<Job>(`/api/sales/jobs/${selected}`),
    enabled: Boolean(selected),
    refetchInterval: (query) => (query.state.data?.status === 'RUNNING' || query.state.data?.status === 'QUEUED' ? 3_000 : false),
  })

  const start = useMutation({
    mutationFn: () =>
      api<{ job_id: string }>('/api/sales/process', {
        method: 'POST',
        body: JSON.stringify({ batch_size: Number(batchSize) }),
      }),
    onSuccess: (data) => {
      setSelected(data.job_id)
      void queryClient.invalidateQueries({ queryKey: ['processing'] })
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const current = status.data?.job

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Hadoop processing jobs"
        subtitle="Each run claims pending MongoDB rows, writes a batch to HDFS, runs the Java MapReduce job on YARN, then builds the Hive fact cube."
        action={
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="label" htmlFor="batch-size">Rows per batch</label>
              <input id="batch-size" type="number" min={1} max={20000} className="input w-32" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} />
            </div>
            <button type="button" className="btn-primary" disabled={start.isPending || status.data?.running} onClick={() => start.mutate()}>
              <Play className="h-4 w-4" /> {status.data?.running ? 'Job running…' : 'Process now'}
            </button>
          </div>
        }
      />

      {start.error && <ErrorBlock error={start.error} />}

      {start.data && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
          Job {start.data.job_id} queued. Watch the stages below.
        </div>
      )}

      {current && (
        <div className="card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold">Latest job</h3>
                <StatusBadge status={current.status} />
                {status.data?.running && <Badge tone="info">live</Badge>}
              </div>
              <p className="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">{current.job_id} · batch {current.batch_id}</p>
            </div>
            <div className="text-right text-xs text-slate-500 dark:text-slate-400">
              <p>Started {dateTime(current.started_at)}</p>
              <p>Duration {duration(current.duration_ms)}</p>
            </div>
          </div>

          <ol className="mt-4 space-y-2">
            {current.stages.map((stage) => (
              <li key={stage.name} className="flex items-start gap-3">
                {stage.status === 'SUCCEEDED' ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-500" />
                ) : stage.status === 'FAILED' ? (
                  <XCircle className="mt-0.5 h-4 w-4 text-rose-500" />
                ) : (
                  <CircleDashed className={`mt-0.5 h-4 w-4 ${stage.status === 'RUNNING' ? 'animate-spin text-brand-500' : 'text-slate-400'}`} />
                )}
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">{stageLabels[stage.name] ?? stage.name.replace(/_/g, ' ')}</span>
                    <StatusBadge status={stage.status} />
                  </div>
                  {Object.keys(stage.details ?? {}).length > 0 && (
                    <p className="mt-0.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                      {Object.entries(stage.details).map(([key, value]) => `${key}=${value}`).join(' · ')}
                    </p>
                  )}
                </div>
              </li>
            ))}
            {current.stages.length === 0 && <li className="text-sm text-slate-500">Waiting for a worker…</li>}
          </ol>

          {current.error && (
            <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 font-mono text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{current.error}</p>
          )}

          <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
            {Object.entries(current.metrics ?? {}).map(([key, value]) => (
              <span key={key} className="rounded-md bg-slate-100 px-2 py-1 dark:bg-slate-800">
                {key}: <strong>{typeof value === 'number' ? count(value) : value}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card overflow-hidden p-0">
        <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold">Job history</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-50 dark:bg-slate-950/50">
              <tr>
                <th className="table-head">Job</th>
                <th className="table-head">Batch</th>
                <th className="table-head">Status</th>
                <th className="table-head">Started</th>
                <th className="table-head text-right">Duration</th>
                <th className="table-head text-right">Rows</th>
                <th className="table-head" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {history.isLoading && (
                <tr><td colSpan={7} className="table-cell text-center text-slate-500">Loading job history…</td></tr>
              )}
              {history.error && (
                <tr><td colSpan={7} className="table-cell text-center text-rose-600 dark:text-rose-400">Could not load job history.</td></tr>
              )}
              {history.data?.items.map((job) => (
                <tr key={job.job_id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="table-cell font-mono text-xs">{job.job_id}</td>
                  <td className="table-cell font-mono text-xs">{job.batch_id}</td>
                  <td className="table-cell"><StatusBadge status={job.status} /></td>
                  <td className="table-cell">{dateTime(job.started_at)}</td>
                  <td className="table-cell text-right">{duration(job.duration_ms)}</td>
                  <td className="table-cell text-right">{job.metrics?.transactions ? count(job.metrics.transactions) : '—'}</td>
                  <td className="table-cell text-right">
                    <button type="button" className="btn-secondary" onClick={() => setSelected(job.job_id)}>Details</button>
                  </td>
                </tr>
              ))}
              {history.data?.items.length === 0 && (
                <tr><td colSpan={7} className="table-cell text-center text-slate-500">No jobs yet. Add transactions, then press Process now.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {detail.isLoading && <Spinner label="Loading job…" />}
      {detail.data && (
        <div className="card">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Job detail — {detail.data.job_id}</h3>
            <button type="button" className="btn-secondary" onClick={() => setSelected(null)}>Close</button>
          </div>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail.data.execution_mode}</p>
          <div className="mt-3 max-h-64 space-y-1 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-200">
            {(detail.data.logs ?? []).map((log, index) => (
              <p key={`${log.ts}-${index}`}>
                <span className="text-slate-500">{new Date(log.ts).toLocaleTimeString()}</span>{' '}
                <span className={log.level === 'ERROR' ? 'text-rose-400' : log.level === 'WARN' ? 'text-amber-300' : 'text-emerald-300'}>{log.level}</span>{' '}
                {log.message}
              </p>
            ))}
            {(detail.data.logs ?? []).length === 0 && <p className="text-slate-500">No log lines stored for this job.</p>}
          </div>
        </div>
      )}
      {detail.error && <ErrorBlock error={detail.error} />}
    </div>
  )
}
