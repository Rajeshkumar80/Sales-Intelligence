import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Boxes, DollarSign, Package, ReceiptText, ShoppingCart } from 'lucide-react'
import { api, qs } from '../api/client'
import type { Overview as OverviewData } from '../api/types'
import { PALETTE, ChartCard, useChartStyle } from '../components/charts'
import { Badge, EmptyBlock, ErrorBlock, KpiCard, SectionHeader, Spinner } from '../components/ui'
import { count, money, moneyCompact } from '../lib/format'

export default function Overview() {
  const chart = useChartStyle()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['overview'],
    queryFn: () => api<OverviewData>(`/api/sales/analytics/overview${qs()}`),
  })

  if (isLoading) return <Spinner label="Loading dashboard…" />
  if (error) return <ErrorBlock error={error} onRetry={() => void refetch()} />

  const kpis = data!.kpis

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Executive overview"
        subtitle="All figures are aggregated from Hive's daily fact cube, materialised by Hadoop MapReduce."
        action={
          <div className="flex items-center gap-2">
            {data!.has_data ? <Badge tone="success">Pipeline data available</Badge> : <Badge tone="warning">No processed data yet</Badge>}
            <Link to="/ingestion" className="btn-primary">
              Ingest data
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Total revenue" value={money(kpis.total_revenue)} icon={<DollarSign className="h-4 w-4" />} hint="Quantity × unit price" />
        <KpiCard label="Transactions" value={count(kpis.total_transactions)} icon={<ReceiptText className="h-4 w-4" />} hint="Raw transactions aggregated by Hive" />
        <KpiCard label="Products" value={count(kpis.total_products)} icon={<Package className="h-4 w-4" />} hint="Distinct product IDs sold" />
        <KpiCard label="Quantity" value={count(kpis.total_quantity)} icon={<Boxes className="h-4 w-4" />} hint="Units sold" />
        <KpiCard label="Avg order value" value={money(kpis.average_order_value)} icon={<ShoppingCart className="h-4 w-4" />} hint="Revenue ÷ transactions" />
      </div>

      {!data!.has_data ? (
        <EmptyBlock
          title="No processed sales data"
          hint="Add transactions manually, upload a CSV or start the simulator, then run the Hadoop pipeline."
          action={
            <Link to="/ingestion" className="btn-primary mt-3">
              Go to Data Ingestion
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <ChartCard title="Revenue trend" subtitle="Daily totals from the fact cube">
              <AreaChart data={data!.daily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={PALETTE[0]} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={PALETTE[0]} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: chart.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: chart.grid }} />
                <YAxis tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} tickLine={false} axisLine={false} width={64} />
                <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
                <Area type="monotone" dataKey="revenue" stroke={PALETTE[0]} strokeWidth={2} fill="url(#revenueFill)" name="Revenue" />
              </AreaChart>
            </ChartCard>
          </div>

          <ChartCard title="Revenue by category" subtitle="Share of total revenue">
            <PieChart>
              <Pie data={data!.category} dataKey="revenue" nameKey="category" innerRadius="55%" outerRadius="80%" paddingAngle={2}>
                {data!.category.map((entry, index) => (
                  <Cell key={entry.category} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
              <Legend formatter={(value) => <span className="text-xs text-slate-600 dark:text-slate-300">{value}</span>} />
            </PieChart>
          </ChartCard>

          <div className="xl:col-span-2">
            <ChartCard title="Top 10 products by revenue" subtitle="From the Hive fact cube, reconciled against MapReduce">
              <BarChart data={data!.top_products} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="product_name" width={170} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
                <Bar dataKey="revenue" name="Revenue" radius={[0, 4, 4, 0]} fill={PALETTE[0]} />
              </BarChart>
            </ChartCard>
          </div>

          <ChartCard title="Revenue by region" subtitle="Filterable in Sales Analytics">
            <BarChart data={data!.region} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="region" tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={moneyCompact} tick={{ fill: chart.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
              <Tooltip contentStyle={chart.tooltip} labelStyle={chart.label} formatter={(value) => money(Number(value))} />
              <Bar dataKey="revenue" name="Revenue" radius={[4, 4, 0, 0]} fill={PALETTE[1]} />
            </BarChart>
          </ChartCard>
        </div>
      )}
    </div>
  )
}
