import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileUp, Pause, Play, Plus, UploadCloud } from 'lucide-react'
import { api } from '../api/client'
import type { SimulatorStatus, UploadReport } from '../api/types'
import { Badge, ErrorBlock, SectionHeader, Spinner } from '../components/ui'
import { count, dateTime } from '../lib/format'

interface Catalog {
  products: { product_id: string; product_name: string; category: string; unit_price: number }[]
  regions: string[]
  categories: string[]
}

interface Stats {
  total: number
  pending: number
  processed: number
}

const emptyForm = { product_id: '', quantity: '1', unit_price: '', region: '', timestamp: '' }

export default function Ingestion() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(emptyForm)
  const [notice, setNotice] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)
  const [interval, setIntervalSeconds] = useState('5')
  const [batchSize, setBatchSize] = useState('20')
  const [report, setReport] = useState<UploadReport | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const catalog = useQuery({ queryKey: ['catalog'], queryFn: () => api<Catalog>('/api/sales/catalog'), staleTime: Infinity })
  const stats = useQuery({
    queryKey: ['txn-stats'],
    queryFn: () => api<Stats>('/api/sales/transactions/stats'),
    refetchInterval: 10_000,
  })
  const simulator = useQuery({
    queryKey: ['simulator'],
    queryFn: () => api<SimulatorStatus>('/api/sales/simulator/status'),
    refetchInterval: 4_000,
  })

  useEffect(() => {
    if (simulator.data?.running) {
      setIntervalSeconds(String(simulator.data.interval_seconds))
      setBatchSize(String(simulator.data.batch_size))
    }
  }, [simulator.data?.running, simulator.data?.interval_seconds, simulator.data?.batch_size])

  const selected = catalog.data?.products.find((product) => product.product_id === form.product_id)

  const create = useMutation({
    mutationFn: () =>
      api('/api/sales/transactions', {
        method: 'POST',
        body: JSON.stringify({
          transaction_id: null,
          product_id: form.product_id,
          product_name: selected?.product_name,
          category: selected?.category,
          quantity: Number(form.quantity),
          unit_price: Number(form.unit_price),
          region: form.region,
          timestamp: form.timestamp ? new Date(form.timestamp).toISOString() : null,
        }),
      }),
    onSuccess: () => {
      setNotice({ tone: 'success', text: 'Transaction stored. It is now pending for the next Hadoop batch.' })
      setForm((current) => ({ ...current, quantity: '1', timestamp: '' }))
      void queryClient.invalidateQueries({ queryKey: ['txn-stats'] })
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (error) => setNotice({ tone: 'danger', text: error instanceof Error ? error.message : 'Insert failed' }),
  })

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData()
      body.append('file', file)
      return api<UploadReport>('/api/sales/transactions/upload', { method: 'POST', body })
    },
    onSuccess: (data) => {
      setReport(data)
      setNotice({ tone: 'success', text: `Upload processed: ${data.inserted} inserted, ${data.duplicates} duplicates, ${data.invalid} invalid.` })
      void queryClient.invalidateQueries({ queryKey: ['txn-stats'] })
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (error) => setNotice({ tone: 'danger', text: error instanceof Error ? error.message : 'Upload failed' }),
  })

  const start = useMutation({
    mutationFn: () =>
      api<SimulatorStatus>('/api/sales/simulator/start', {
        method: 'POST',
        body: JSON.stringify({ interval_seconds: Number(interval), batch_size: Number(batchSize) }),
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['simulator'] }),
  })

  const stop = useMutation({
    mutationFn: () => api<SimulatorStatus>('/api/sales/simulator/stop', { method: 'POST' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['simulator'] }),
  })

  const submitManual = (event: React.FormEvent) => {
    event.preventDefault()
    setNotice(null)
    if (!form.product_id || !form.region) {
      setNotice({ tone: 'danger', text: 'Choose a product and a region first.' })
      return
    }
    create.mutate()
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Data ingestion"
        subtitle="Three independent entry points: manual form, validated CSV upload, and a live simulator. All rows land in MongoDB as pending."
        action={
          <div className="flex gap-2">
            <Badge tone="info">{count(stats.data?.pending ?? 0)} pending</Badge>
            <Badge tone="success">{count(stats.data?.processed ?? 0)} processed</Badge>
          </div>
        }
      />

      {notice && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${notice.tone === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200' : 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200'}`}>
          {notice.text}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <form className="card space-y-3" onSubmit={submitManual}>
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-brand-600" />
            <h3 className="text-sm font-semibold">Manual transaction</h3>
          </div>
          <div>
            <label className="label" htmlFor="product">Product</label>
            <select
              id="product"
              className="input"
              value={form.product_id}
              onChange={(e) => {
                const product = catalog.data?.products.find((item) => item.product_id === e.target.value)
                setForm((current) => ({ ...current, product_id: e.target.value, unit_price: product ? String(product.unit_price) : '' }))
              }}
            >
              <option value="">Select a product…</option>
              {catalog.data?.products.map((product) => (
                <option key={product.product_id} value={product.product_id}>
                  {product.product_name} · {product.category}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="quantity">Quantity</label>
              <input id="quantity" type="number" min={1} max={100000} className="input" value={form.quantity} onChange={(e) => setForm((c) => ({ ...c, quantity: e.target.value }))} required />
            </div>
            <div>
              <label className="label" htmlFor="unit-price">Unit price (USD)</label>
              <input id="unit-price" type="number" min={0} step="0.01" className="input" value={form.unit_price} onChange={(e) => setForm((c) => ({ ...c, unit_price: e.target.value }))} required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="region-select">Region</label>
              <select id="region-select" className="input" value={form.region} onChange={(e) => setForm((c) => ({ ...c, region: e.target.value }))} required>
                <option value="">Select…</option>
                {catalog.data?.regions.map((region) => <option key={region} value={region}>{region}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="timestamp">Timestamp (UTC, optional)</label>
              <input id="timestamp" type="datetime-local" className="input" value={form.timestamp} onChange={(e) => setForm((c) => ({ ...c, timestamp: e.target.value }))} />
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={create.isPending}>
            <Plus className="h-4 w-4" /> {create.isPending ? 'Saving…' : 'Add transaction'}
          </button>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Transaction IDs are generated server-side. A duplicate ID is rejected with HTTP 409.
          </p>
        </form>

        <div className="space-y-4">
          <div className="card space-y-3">
            <div className="flex items-center gap-2">
              <UploadCloud className="h-4 w-4 text-brand-600" />
              <h3 className="text-sm font-semibold">CSV upload</h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Required columns: transaction_id, product_id, product_name, category, quantity, unit_price, region, timestamp.
              Max 5 MB / 50,000 rows. Duplicates and invalid rows are reported, never silently dropped.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700 dark:text-slate-300"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary"
                disabled={upload.isPending}
                onClick={() => {
                  const file = fileRef.current?.files?.[0]
                  if (!file) {
                    setNotice({ tone: 'danger', text: 'Choose a CSV file first.' })
                    return
                  }
                  setNotice(null)
                  upload.mutate(file)
                }}
              >
                <FileUp className="h-4 w-4" /> {upload.isPending ? 'Uploading…' : 'Upload CSV'}
              </button>
              <a className="btn-secondary" href="/api/sales/transactions/template.csv">Download template</a>
            </div>
          </div>

          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Play className="h-4 w-4 text-brand-600" />
                <h3 className="text-sm font-semibold">Live simulator</h3>
              </div>
              {simulator.data?.running ? <Badge tone="success">Running</Badge> : <Badge tone="neutral">Stopped</Badge>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label" htmlFor="interval">Interval (seconds)</label>
                <input id="interval" type="number" min={1} max={120} className="input" value={interval} onChange={(e) => setIntervalSeconds(e.target.value)} disabled={simulator.data?.running} />
              </div>
              <div>
                <label className="label" htmlFor="batch">Rows per tick</label>
                <input id="batch" type="number" min={1} max={500} className="input" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} disabled={simulator.data?.running} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-primary" onClick={() => start.mutate()} disabled={simulator.data?.running || start.isPending}>
                <Play className="h-4 w-4" /> Start
              </button>
              <button type="button" className="btn-secondary" onClick={() => stop.mutate()} disabled={!simulator.data?.running || stop.isPending}>
                <Pause className="h-4 w-4" /> Stop
              </button>
            </div>
            {simulator.data && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {count(simulator.data.generated)} rows generated in {simulator.data.ticks} ticks
                {simulator.data.started_at ? ` · started ${dateTime(simulator.data.started_at)}` : ''}
                {simulator.data.last_error ? ` · last error: ${simulator.data.last_error}` : ''}
              </p>
            )}
          </div>
        </div>
      </div>

      {report && (
        <div className="card">
          <h3 className="text-sm font-semibold">Upload report — {report.filename}</h3>
          <div className="mt-2 grid gap-3 sm:grid-cols-4">
            <div><p className="text-xs uppercase text-slate-500">Rows</p><p className="text-lg font-semibold">{count(report.rows_total)}</p></div>
            <div><p className="text-xs uppercase text-slate-500">Inserted</p><p className="text-lg font-semibold text-emerald-600">{count(report.inserted)}</p></div>
            <div><p className="text-xs uppercase text-slate-500">Duplicates</p><p className="text-lg font-semibold text-amber-600">{count(report.duplicates)}</p></div>
            <div><p className="text-xs uppercase text-slate-500">Invalid</p><p className="text-lg font-semibold text-rose-600">{count(report.invalid)}</p></div>
          </div>
          {report.invalid_details.length > 0 && (
            <div className="mt-3 max-h-48 overflow-auto rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              {report.invalid_details.map((item) => (
                <p key={`${item.row}-${item.error}`} className="font-mono text-rose-600 dark:text-rose-400">row {item.row}: {item.error}</p>
              ))}
            </div>
          )}
          {report.duplicate_details.length > 0 && (
            <div className="mt-3 max-h-40 overflow-auto rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
              {report.duplicate_details.map((item) => (
                <p key={item.transaction_id} className="font-mono text-amber-600 dark:text-amber-400">{item.transaction_id}: already stored</p>
              ))}
            </div>
          )}
        </div>
      )}

      {(create.isPending || upload.isPending) && <Spinner label="Writing to MongoDB Atlas…" />}
      {create.error && <ErrorBlock error={create.error} />}
      {upload.error && <ErrorBlock error={upload.error} />}
    </div>
  )
}
