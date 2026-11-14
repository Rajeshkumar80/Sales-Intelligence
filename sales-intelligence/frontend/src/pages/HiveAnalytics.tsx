import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../api/client'
import type { HiveRow, ProductRow, Snapshot } from '../api/types'
import { Badge, EmptyBlock, ErrorBlock, SectionHeader, Segmented, Spinner } from '../components/ui'
import { count, dateTime, money } from '../lib/format'

const sections = ['product', 'category', 'region', 'daily', 'monthly', 'total'] as const

export default function HiveAnalytics() {
  const [section, setSection] = useState<(typeof sections)[number]>('product')

  const hive = useQuery({
    queryKey: ['hive-results'],
    queryFn: () => api<{ snapshot: Snapshot | null }>('/api/sales/analytics/hive-results'),
  })
  const mr = useQuery({
    queryKey: ['mr-results'],
    queryFn: () => api<{ batch_id: string | null; items: ProductRow[] }>('/api/sales/analytics/mr-results'),
  })

  if (hive.isLoading) return <Spinner label="Loading Hive snapshot…" />
  if (hive.error) return <ErrorBlock error={hive.error} onRetry={() => void hive.refetch()} />

  const snapshot = hive.data?.snapshot
  if (!snapshot) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Hive analytics" subtitle="Results of the Hive queries over the ORC fact cube." />
        <EmptyBlock title="No Hive snapshot yet" hint="Run the Hadoop pipeline once. Hive results are stored per batch and shown here." />
      </div>
    )
  }

  const rows = snapshot.hive_results.filter((row) => row.section === section)
  const reconciliation = snapshot.reconciliation

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Hive analytics"
        subtitle={`Batch ${snapshot.batch_id} · snapshot generated ${dateTime(snapshot.generated_at)}`}
        action={<Badge tone={reconciliation.match ? 'success' : 'danger'}>{reconciliation.match ? 'MR = Hive' : 'Reconciliation mismatch'}</Badge>}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className={`card lg:col-span-2 ${reconciliation.match ? 'border-emerald-200 dark:border-emerald-900' : 'border-rose-200 dark:border-rose-900'}`}>
          <div className="flex items-start gap-3">
            {reconciliation.match ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-500" /> : <XCircle className="mt-0.5 h-5 w-5 text-rose-500" />}
            <div className="flex-1">
              <h3 className="text-sm font-semibold">MapReduce vs Hive reconciliation</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                The Java reducer sums revenue per product ID; Hive sums the same rows into the daily fact cube. Differences beyond {money(reconciliation.tolerance)} are flagged.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase text-slate-500">MapReduce revenue</p>
                  <p className="text-lg font-semibold">{money(reconciliation.mr_revenue)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500">Hive revenue</p>
                  <p className="text-lg font-semibold">{money(reconciliation.hive_revenue)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500">Delta</p>
                  <p className="text-lg font-semibold">{money(reconciliation.delta_revenue)}</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Quantity {count(reconciliation.mr_quantity)} vs {count(reconciliation.hive_quantity)} · orders {count(reconciliation.mr_orders)} vs {count(reconciliation.hive_orders)} · {reconciliation.products} products
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold">MapReduce counters</h3>
          <dl className="mt-2 space-y-1 text-sm">
            {Object.entries(snapshot.mr_counters).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-2">
                <dt className="text-slate-500 dark:text-slate-400">{key}</dt>
                <dd className="font-medium">{count(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3 dark:border-slate-800">
          <Segmented
            value={section}
            options={sections.map((option) => ({ value: option, label: option }))}
            onChange={setSection}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-50 dark:bg-slate-950/50">
              <tr>
                <th className="table-head">{section === 'product' ? 'Product' : section === 'daily' ? 'Date' : section === 'monthly' ? 'Month' : section === 'total' ? 'Scope' : section}</th>
                <th className="table-head">{section === 'product' ? 'Product ID' : 'Key'}</th>
                <th className="table-head text-right">Revenue</th>
                <th className="table-head text-right">Quantity</th>
                <th className="table-head text-right">Orders</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((row: HiveRow) => (
                <tr key={`${row.section}-${row.key}`}>
                  <td className="table-cell font-medium">{row.label}</td>
                  <td className="table-cell font-mono text-xs">{row.key}</td>
                  <td className="table-cell text-right">{money(row.revenue)}</td>
                  <td className="table-cell text-right">{count(row.quantity)}</td>
                  <td className="table-cell text-right">{count(row.orders)}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={5} className="table-cell text-center text-slate-500">No rows in this section.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h3 className="text-sm font-semibold">MapReduce output — product totals</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Read directly from HDFS <span className="font-mono">/bda/sales/revenue/batch_id={snapshot.batch_id}/part-r-00000</span></p>
        </div>
        <div className="max-h-96 overflow-auto">
          <table className="min-w-full">
            <thead className="sticky top-0 bg-slate-50 dark:bg-slate-950">
              <tr>
                <th className="table-head">Product</th>
                <th className="table-head">Product ID</th>
                <th className="table-head text-right">Revenue</th>
                <th className="table-head text-right">Quantity</th>
                <th className="table-head text-right">Orders</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {mr.isLoading && (
                <tr><td colSpan={5} className="table-cell text-center text-slate-500">Loading MapReduce output…</td></tr>
              )}
              {mr.error && (
                <tr><td colSpan={5} className="table-cell text-center text-rose-600 dark:text-rose-400">Could not load MapReduce output.</td></tr>
              )}
              {mr.data?.items.map((row) => (
                <tr key={row.product_id}>
                  <td className="table-cell">{row.product_name}</td>
                  <td className="table-cell font-mono text-xs">{row.product_id}</td>
                  <td className="table-cell text-right">{money(row.revenue)}</td>
                  <td className="table-cell text-right">{count(row.quantity)}</td>
                  <td className="table-cell text-right">{count(row.orders)}</td>
                </tr>
              ))}
              {!mr.isLoading && !mr.error && !mr.data?.items.length && (
                <tr><td colSpan={5} className="table-cell text-center text-slate-500">No MapReduce rows stored.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
