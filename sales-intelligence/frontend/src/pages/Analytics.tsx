import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'
import { api, qs } from '../api/client'
import type { FilterOptions, Overview as OverviewData } from '../api/types'
import { ChartCard, PALETTE, useChartStyle } from '../components/charts'
import { Badge, ErrorBlock, KpiCard, SectionHeader, Segmented, Spinner } from '../components/ui'
import { count, money, moneyCompact, monthLabel } from '../lib/format'

const emptyFilters = { date_from: '', date_to: '', product_id: '', category: '', region: '' }

export default function Analytics() {
  const chart = useChartStyle()
  const [filters, setFilters] = useState(emptyFilters)
  const [trend, setTrend] = useState<'daily' | 'monthly'>('daily')

  const options = useQuery({
    queryKey: ['options'],
    queryFn: () => api<FilterOptions>('/api/sales/analytics/options'),
    staleTime: 60_000,
  })

  const query = qs(filters)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics', query],
    queryFn: () => api<OverviewData>(`/api/sales/analytics/overview${query}`),
  })

  const active = useMemo(() => Object.values(filters).filter(Boolean).length, [filters])
  const set = (key: keyof typeof filters, value: string) => setFilters((current) => ({ ...current, [key]: value }))

  const trendData = data ? (trend === 'daily' ? data.daily : data.monthly) : []

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Sales analytics"
        subtitle="Filter the Hive fact cube by date, product, category and region. Every chart re-queries the backend."
        action={
          <div className="flex items-center gap-2">
            {active > 0 && <Badge tone="info">{active} filter{active === 1 ? '' : 's'} active</Badge>}
            <button type="button" className="btn-secondary" onClick={() => setFilters(emptyFilters)} disabled={active === 0}>
              Reset filters
            </button>
          </div>
        }
      />

      <div className="card grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div>
          <label className="label" htmlFor="date-from">From</label>
          <input id="date-from" type="date" className="input" value={filters.date_from} onChange={(e) => set('date_from', e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="date-to">To</label>
          <input id="date-to" type="date" className="input" value={filters.date_to} onChange={(e) => set('date_to', e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="product">Product</label>
          <select id="product" className="input" value={filters.product_id} onChange={(e) => set('product_id', e.target.value)}>
            <option value="">All products</option>
            {options.data?.products.map((product) => (
              <option key={product.product_id} value={product.product_id}>
                {product.product_name} ({product.product_id})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="category">Category</label>
          <select id="category" className="input" value={filters.category} onChange={(e) => set('category', e.target.value)}>
            <option value="">All categories</option>
            {options.data?.categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="region">Region</label>
          <select id="region" className="input" value={filters.region} onChange={(e) => set('region', e.target.value)}>
            <option value="">All regions</option>
            {options.data?.regions.map((region) => (
              <option key={region} value={region}>{region}</option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <Spinner label="Aggregating…" />}
      {error && <ErrorBlock error={error} onRetry={() => void refetch()} />}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Revenue" value={money(data.kpis.total_revenue)} />
            <KpiCard label="Quantity" value={count(data.kpis.total_quantity)} />
            <KpiCard label="Transactions" value={count(data.kpis.total_transactions)} />
            <KpiCard label="Products" value={count(data.kpis.total_products)} />
          </div>

          <ChartCard
            title={trend === 'daily' ? 'Daily revenue' : 'Monthly revenue'}
            subtitle="Hive fact cube, grouped by sale date"
            isEmpty={trendData.length === 0}
            action={
              <Segmented
                value={trend}
                options={[
                  { value: 'daily', label: 'Daily' },
                  { value: 'monthly', label: 'Monthly' },
                ] as const}
                onChange={setTrend}
              />
            }
          >
            <AreaChart data={trendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey={trend === 'daily' ? 'date' : 'month'}
                tickFormatter={trend === 'monthly' ? monthLabel : undefined}
                tick={{ fill: chart.axis, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
              <Tooltip
                contentStyle={chart.tooltip}
                labelStyle={chart.label}
                labelFormatter={(value) => (trend === 'monthly' ? monthLabel(String(value)) : String(value))}
                formatter={(value) => money(Number(value))}
              />
              <Area type="monotone" dataKey="revenue" name="Revenue" stroke={PALETTE[0]} strokeWidth={2} fill={PALETTE[0]} fillOpacity={0.12} />
            </AreaChart>
          </ChartCard>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartCard title="Revenue by category" isEmpty={data.category.length === 0}>
              <BarChart data={data.category} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="category" tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
                <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
                <Bar dataKey="revenue" name="Revenue" fill={PALETTE[5]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartCard>

            <ChartCard title="Revenue by region" isEmpty={data.region.length === 0}>
              <BarChart data={data.region} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="region" tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
                <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
                <Bar dataKey="revenue" name="Revenue" fill={PALETTE[1]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartCard>
          </div>

          <div className="card overflow-hidden p-0">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <h3 className="text-sm font-semibold">Top 10 products by revenue</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-slate-50 dark:bg-slate-950/50">
                  <tr>
                    <th className="table-head">Product</th>
                    <th className="table-head">Product ID</th>
                    <th className="table-head text-right">Revenue</th>
                    <th className="table-head text-right">Quantity</th>
                    <th className="table-head text-right">Orders</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {data.top_products.map((product) => (
                    <tr key={product.product_id}>
                      <td className="table-cell font-medium">{product.product_name}</td>
                      <td className="table-cell font-mono text-xs">{product.product_id}</td>
                      <td className="table-cell text-right">{money(product.revenue)}</td>
                      <td className="table-cell text-right">{count(product.quantity)}</td>
                      <td className="table-cell text-right">{count(product.orders)}</td>
                    </tr>
                  ))}
                  {data.top_products.length === 0 && (
                    <tr><td className="table-cell text-center text-slate-500" colSpan={5}>No products match these filters.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
