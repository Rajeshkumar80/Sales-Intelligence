import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'
import { api, downloadCsv, qs } from '../api/client'
import type { FilterOptions, Paged, Transaction } from '../api/types'
import { Badge, ErrorBlock, SectionHeader, Spinner } from '../components/ui'
import { count, dateTime, money } from '../lib/format'

export default function Transactions() {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [region, setRegion] = useState('')
  const [category, setCategory] = useState('')
  const [processed, setProcessed] = useState('')
  const [sort, setSort] = useState('-timestamp')
  const [page, setPage] = useState(1)
  const pageSize = 25

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(search)
      setPage(1)
    }, 350)
    return () => window.clearTimeout(timer)
  }, [search])

  const filters = { search: debounced, region, category, processed: processed === '' ? '' : processed, sort }
  const query = qs({ ...filters, page, page_size: pageSize })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['transactions', query],
    queryFn: () => api<Paged<Transaction>>(`/api/sales/transactions${query}`),
  })
  const options = useQuery({
    queryKey: ['options'],
    queryFn: () => api<FilterOptions>('/api/sales/analytics/options'),
    staleTime: 60_000,
  })

  const toggleSort = (field: string) => {
    setSort((current) => (current === field ? `-${field}` : field))
    setPage(1)
  }

  const header = (field: string, label: string, align = 'left') => (
    <th className={`table-head ${align === 'right' ? 'text-right' : ''}`}>
      <button type="button" className="inline-flex items-center gap-1 hover:text-slate-900 dark:hover:text-white" onClick={() => toggleSort(field)}>
        {label}
        {sort === field && <ArrowUp className="h-3 w-3" />}
        {sort === `-${field}` && <ArrowDown className="h-3 w-3" />}
      </button>
    </th>
  )

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Transaction history"
        subtitle="Raw transactions stored in MongoDB Atlas. Processed rows are already part of the Hive cube."
        action={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => downloadCsv(`/api/sales/reports/export/transactions.csv${qs(filters)}`, 'sales-transactions.csv')}
          >
            <Download className="h-4 w-4" /> Export CSV
          </button>
        }
      />

      <div className="card grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <label className="label" htmlFor="search">Search</label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input id="search" className="input pl-9" placeholder="Search transactions…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="region-filter">Region</label>
          <select id="region-filter" className="input" value={region} onChange={(e) => { setRegion(e.target.value); setPage(1) }}>
            <option value="">All regions</option>
            {options.data?.regions.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="category-filter">Category</label>
          <select id="category-filter" className="input" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }}>
            <option value="">All categories</option>
            {options.data?.categories.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="processed-filter">Pipeline state</label>
          <select id="processed-filter" className="input" value={processed} onChange={(e) => { setProcessed(e.target.value); setPage(1) }}>
            <option value="">All rows</option>
            <option value="false">Pending</option>
            <option value="true">Processed</option>
          </select>
        </div>
      </div>

      {isLoading && <Spinner label="Loading transactions…" />}
      {error && <ErrorBlock error={error} onRetry={() => void refetch()} />}

      {data && (
        <div className="card overflow-hidden p-0">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {count(data.total)} transactions · page {data.page} of {data.pages}
            </p>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="h-4 w-4" /> Previous
              </button>
              <button type="button" className="btn-secondary" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-slate-50 dark:bg-slate-950/50">
                <tr>
                  {header('timestamp', 'Timestamp')}
                  {header('product_name', 'Product')}
                  <th className="table-head">Transaction</th>
                  {header('category', 'Category')}
                  {header('region', 'Region')}
                  {header('quantity', 'Qty', 'right')}
                  <th className="table-head text-right">Unit price</th>
                  {header('revenue', 'Revenue', 'right')}
                  <th className="table-head">Source</th>
                  <th className="table-head">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.items.map((transaction) => (
                  <tr key={transaction.transaction_id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                    <td className="table-cell whitespace-nowrap">{dateTime(transaction.timestamp)}</td>
                    <td className="table-cell">
                      <span className="font-medium">{transaction.product_name}</span>
                      <span className="ml-2 font-mono text-xs text-slate-500">{transaction.product_id}</span>
                    </td>
                    <td className="table-cell font-mono text-xs">{transaction.transaction_id}</td>
                    <td className="table-cell">{transaction.category}</td>
                    <td className="table-cell">{transaction.region}</td>
                    <td className="table-cell text-right">{transaction.quantity}</td>
                    <td className="table-cell text-right">{money(transaction.unit_price)}</td>
                    <td className="table-cell text-right font-medium">{money(transaction.revenue)}</td>
                    <td className="table-cell capitalize">{transaction.source}</td>
                    <td className="table-cell">
                      {transaction.processed ? <Badge tone="success">Processed</Badge> : <Badge tone="warning">Pending</Badge>}
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr><td className="table-cell text-center text-slate-500" colSpan={10}>No transactions match these filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
